from frappe.model.document import Document
import frappe
from frappe.utils import now_datetime, nowdate, today
from frappe.utils import getdate, add_days, cint
import os, urllib
import json

class Claim(Document):

    def validate(self):
            self.validate_mrcms_rules()

            self.set_comment_meta()
            self.prevent_edit_others_comments()
    
            if not self.amount_claimed:
                return
    
            # ALWAYS derive category from amount
            new_category = get_claim_category_by_amount(self.amount_claimed)
    
            category_changed = self.claim_category != new_category
            # self.claim_category = new_category
    
            # Re-populate documents if category changed or empty
            if category_changed or not self.claim_required_documents:
                self.populate_required_documents()

    def after_insert(self):
        """Log creation of a new Claim"""
        # Optional: You may still log creation if needed
        # self.log_claim_process("Created")
        self.populate_required_documents()

    def on_workflow_action(self, action):
        self.lock_previous_comments()

    def on_update(self):
        # self.log_claim_process("Created")
        self.validate_entitlement_period()

        prev = self.get_doc_before_save()
        prev_amount = prev.amount_claimed if prev else None
        prev_category = prev.claim_category if prev else None
 
        if (
            self.amount_claimed != prev_amount or
            self.claim_category != prev_category
        ):
            self.populate_required_documents()

    def before_save(self):
        for row in self.claim_remarks:
            if row.comment_by and not row.comment_by_full_name:
                user = frappe.get_doc("User", row.comment_by)
                row.comment_by_full_name = user.full_name
                row.comment_by_authority = user.authority
 
 
            previous_doc = self.get_doc_before_save()
            if previous_doc:
                self.log_claim_status_change(previous_doc)

            self.validate_entitlement_period()

        # Populate IP Communication with logged-in user and date
        for row in self.get("ip_communication") or []:
            # Skip rows that already have a user
            if row.contacted_by:
                continue
            # Set date if missing
            if not row.date:
                row.date = today()
            # Always set logged-in user
            row.contacted_by = frappe.session.user

        # ------------------------------
        # Fetch active rule for category
        # ------------------------------
        rule = frappe.get_all(
            "Claim Document Rule",
            filters={
                "claim_category": self.claim_category,
                "is_active": 1
            },
            fields=["name"],
            limit=1
        )
 
        rule_map = {}
 
        if rule:
            rule_details = frappe.get_all(
                "Claim Document Rule Details",
                filters={"parent": rule[0].name},
                fields=["claim_doc_master", "mandatory"]
            )
 
            rule_map = {
                d.claim_doc_master: d.mandatory for d in rule_details
            }
 
        # ------------------------------
        # FILE SIZE SETTINGS (ADDED)
        # ------------------------------
        settings = frappe.get_single("Mrcms Settings")
        size = settings.upload_file_size or 0
        unit = getattr(settings, "upload_file_size_unit", "MB")
 
        if unit == "KB":
            max_bytes = size * 1024
        else:
            max_bytes = size * 1024 * 1024
 
        # ------------------------------
        # Loop child table
        # ------------------------------
        for row in self.claim_required_documents:
 
            # -------------------
            # Set mandatory from rule
            # -------------------
            if row.claim_doc_master:
                row.mandatory = int(rule_map.get(row.claim_doc_master, 0))
 
            if row.uploaded_file:
                if not row.uploaded_on:
                    row.uploaded_on = now_datetime()
                if not row.uploaded_by:
                    row.uploaded_by = frappe.session.user
 
                # FILE SIZE CHECK
                file_doc = frappe.get_all(
                    "File",
                    filters={"file_url": row.uploaded_file},
                    fields=["file_size", "file_name"],
                    limit=1
                )
 
                if file_doc and file_doc[0].file_size:
                    if file_doc[0].file_size > max_bytes:
                        frappe.throw(
                            f"File size exceeds maximum allowed size of "
                            f"{size} {unit} for {row.claim_doc_master}"
                        )
 
                # FILE EXTENSION CHECK
                doc_master = frappe.get_doc("Claim Document Master", row.claim_doc_master)
                allowed_extensions = []
                if doc_master.file_type_jpg: allowed_extensions.append("jpg")
                if doc_master.file_type_jpeg: allowed_extensions.append("jpeg")
                if doc_master.file_type_png: allowed_extensions.append("png")
                if doc_master.file_type_gif: allowed_extensions.append("gif")
                if doc_master.file_type_pdf: allowed_extensions.append("pdf")
 
                filename = os.path.basename(urllib.parse.unquote(row.uploaded_file)).strip()
                ext = filename.split('.')[-1].lower()
 
                if ext not in allowed_extensions:
                    frappe.throw(
                        f"Invalid file type for {doc_master.document_name}. "
                        f"Allowed types: {', '.join(allowed_extensions)}"
                    )

    # Fetch ONLY the entitlement period(s) that COVER / OVERLAP the treatment period (from_date → to_date)
    def before_print(self, print_settings=None):
 
        if not self.from_date or not self.to_date or not self.ip_no:
            self.entitled_periods = "--"
            return
 
        entitlements = frappe.get_all(
            "Entitlement",
            filters={
                "parent": self.ip_no,
                "parenttype": "Insured Person",
                "start_date": ("<=", self.to_date),
                "end_date": (">=", self.from_date),
            },
            fields=["start_date", "end_date"],
            order_by="start_date asc"
        )
 
        if entitlements:
            periods = [
                f"{frappe.utils.formatdate(e.start_date, 'dd-mm-yyyy')} to "
                f"{frappe.utils.formatdate(e.end_date, 'dd-mm-yyyy')}"
                for e in entitlements
            ]
 
            # Multiple only if treatment spans multiple entitlement slabs
            self.entitled_periods = "<br><br><br>".join(periods)
        else:
            self.entitled_periods = "--"
            
    def on_submit(self):
        """Log submission of the Claim"""
        # self.log_claim_process("Submitted")
        self.validate_entitlement_period()
        for row in self.claim_required_documents:
            if row.mandatory == "Yes" and not row.uploaded_file:
                frappe.throw(
                    f"Mandatory document missing: {row.claim_doc_name or row.claim_doc_master}"
                )

    def validate_entitlement_period(self):
        """
        Ensure treatment period (from_date -> to_date) is fully covered by
        one or more contiguous entitlement periods (no gaps), even if
        it crosses multiple 6-month rows (e.g. Jun → Jul).
        """

        if not (self.ip_no and self.from_date and self.to_date):
            frappe.throw(_("IP No, From Date and To Date are mandatory for entitlement check."))

        # Fetch entitlement rows from Insured Person
        entitlements = frappe.get_all(
            "Entitlement",
            filters={
                "parent": self.ip_no,
                "parenttype": "Insured Person",
                "parentfield": "entitlement",
            },
            fields=["start_date", "end_date"],
            order_by="start_date asc",
        )

        if not entitlements:
            frappe.throw(f"No entitlement periods are configured for Insured Person {0}. "
                "Please update entitlement periods before processing the claim."
                         .format(self.ip_no))

        claim_from = getdate(self.from_date)
        claim_to   = getdate(self.to_date)

        # --- 1) Normalise & sort intervals ---
        intervals = []
        for ent in entitlements:
            if ent.start_date and ent.end_date:
                intervals.append((
                    getdate(ent.start_date),
                    getdate(ent.end_date),
                ))

        # Safety: if somehow no valid intervals
        if not intervals:
            frappe.throw(
                f"No valid entitlement date ranges found for Insured Person {0}."
            ).format(self.ip_no)

        intervals.sort(key=lambda x: x[0])  # sort by start_date

        # --- 2) Merge overlapping / contiguous intervals ---
        merged = []
        cur_start, cur_end = intervals[0]

        for start, end in intervals[1:]:
            # If next interval starts on or before the day after current end,
            # we treat it as continuous coverage and merge.
            if start <= add_days(cur_end, 1):
                # Extend the current interval
                if end > cur_end:
                    cur_end = end
            else:
                # Gap detected, push current and start a new one
                merged.append((cur_start, cur_end))
                cur_start, cur_end = start, end

        # Push the last interval
        merged.append((cur_start, cur_end))

        # --- 3) Check if any merged interval fully covers claim period ---
        allowed = False
        for start, end in merged:
            if claim_from >= start and claim_to <= end:
                allowed = True
                break

        if not allowed:
            msg = (
                f"Treatment period {0} to {1} does not fall within any continuous "
                "entitlement coverage for Insured Person {2}. Claim cannot be processed."
            ).format(claim_from, claim_to, self.ip_no)
            frappe.throw(msg)


    def log_claim_process(self, action, current_state, next_state):
        """
        Logs ONLY workflow-related actions.
        Stores both CURRENT and NEXT workflow states.
        Calculates duration_seconds correctly.
        """
 
        from frappe.utils import now_datetime
 
        now = now_datetime()
        user = frappe.session.user
        user_doc = frappe.get_doc("User", user)
 
        #  Update duration of previous log (IN MEMORY)
        if self.get("claim_process"):
            last_row = self.get("claim_process")[-1]
 
            if last_row.date:
                duration = int((now - last_row.date).total_seconds())
                last_row.duration_seconds = duration
 
        #  Append new workflow log
        self.append("claim_process", {
            "date": now,
            "activity": action,
            "current_state": current_state,
            "claim_status_log": next_state,
            "user": user,
            "organisation": getattr(user_doc, "organisation", None),
            "user_full_name": user_doc.full_name,
            "user_authority": getattr(user_doc, "authority", None)
        })
 
 
    def log_claim_status_change(self, previous_doc):
        """
        Log ONLY when workflow_state changes.
        """
 
        if not previous_doc:
            return
 
        old_state = previous_doc.workflow_state   # CURRENT workflow state
        new_state = self.workflow_state           # NEXT workflow state
 
        #  No workflow change → skip logging
        if old_state == new_state:
            return
 
        if new_state and not frappe.db.exists("Workflow State", new_state):
            frappe.throw(f"Invalid Workflow State: {new_state}")
 
        #  Activity = Claim Status
        activity_text = self.claim_status
 
        # Log workflow transition
        self.log_claim_process(
            action=activity_text,
            current_state=old_state,
            next_state=new_state
        )

    def populate_required_documents(self):
        if not self.claim_category:
            return
 
        # Clear existing rows
        self.set("claim_required_documents", [])
 
        rules = frappe.get_all(
            "Claim Document Rule",
            filters={
                "claim_category": self.claim_category,
                "is_active": 1
            },
            pluck="name"
        )
 
        if not rules:
            return
 
        added = set()
 
        for rule in rules:
            rule_doc = frappe.get_doc("Claim Document Rule", rule)
 
            for r in rule_doc.claim_document_rule_details:
                if not r.claim_doc_master or r.claim_doc_master in added:
                    continue
 
                # Fetch document name ONLY from master
                doc_name = frappe.db.get_value(
                    "Claim Document Master",
                    r.claim_doc_master,
                    "document_name"
                )
 
                # Mandatory MUST come from rule details
                self.append("claim_required_documents", {
                    "claim_doc_master": r.claim_doc_master,
                    "claim_doc_name": doc_name,
                    "mandatory": int(r.mandatory)  
                })
 
            added.add(r.claim_doc_master)

    # ---------------------------
    # COMMENT META (auto user)
    # ---------------------------
    def set_comment_meta(self):
        user = frappe.session.user
        for row in self.claim_remarks:
            if not row.comment_by:
                row.comment_by = user
                row.claim_status = self.claim_status
                row.date = now_datetime()


    # ---------------------------
    # LOCKING LOGIC
    # ---------------------------
    def lock_previous_comments(self):
        """
        Only lock comments by other users once the current authority acts
        """
        current_user = frappe.session.user
        for row in self.claim_remarks:
            if row.comment_by != current_user and not row.is_locked:
                row.is_locked = 1
                row.is_seen = 1

    # ---------------------------
    # PREVENT EDIT
    # ---------------------------
    def prevent_edit_others_comments(self):
            before = self.get_doc_before_save()
            if not before:
                return
 
            for old, new in zip(before.claim_remarks, self.claim_remarks):
                # Only allow editing by the original commenter
                if old.comment_by != frappe.session.user and old.comment != new.comment:
                    frappe.throw(f"You cannot edit remarks by {old.comment_by}.")
 
                # If the comment is locked by next authority, even owner cannot edit
                if old.is_locked and old.comment != new.comment:
                    frappe.throw("You cannot edit this remark because next authority has processed it.")

    def validate_mrcms_rules(self):
        settings = frappe.get_single("Mrcms Settings")
 
        prev = self.get_doc_before_save()
        if not prev:
            return
 
        if prev.workflow_state == self.workflow_state:
            return
 
        if self.workflow_state != "HC Review":
            return
 
        # -----------------------------
        # Claim Checklist Validation
        # -----------------------------
        if settings.validate_claim_checklist:
            for row in self.claim_checklist or []:
                if row.required == "Yes":
                    if not row.present:
                        frappe.throw(
                            f"❌ Checklist item '{row.criteria}' is required but not marked as Present."
                        )
                   
 
        # ---------------------------------
        # Required Documents Validation
        # ---------------------------------
        if settings.validate_required_documents:
            missing = []
 
            for row in self.claim_required_documents or []:
                if cint(row.mandatory):
                    if not row.uploaded_file or not str(row.uploaded_file).strip():
                        missing.append(row.claim_doc_name or row.claim_doc_master)
 
            # Throw AFTER checking all rows
            if missing:
                frappe.throw(
                    "Please upload all mandatory documents before approval.<br><br>"
                    "<b>Missing documents:</b><br>"
                    + "<br>".join(missing),
                    title="Mandatory Documents Required"
                )
# def get_permission_query_conditions(user):
    # pass
    """
    Return a SQL WHERE clause fragment as a string to restrict records
    visible to the given user.
    """
    # if not user:
    #     user = frappe.session.user
        
    # user_escaped = frappe.db.escape(user)

    # user = frappe.get_doc("User", frappe.user)
    # user_roles = [r.role for r in user.roles]
    # is_admin = "CRM Manager" in user_roles
    # if not is_admin:
    #     conditions = f'lead_owner = {user_escaped} OR owner = {user_escaped}'
    # return conditions

# def get_permission_query_conditions(user):
#     # Fallback to session user if not passed
#     if not user:
#         user = frappe.session.user

#     # Allow full access to admins (adjust roles if needed)
#     if user in ("Administrator"):
#         return ""

#     # If you have a special role that should see all claims:
#     if "MRCMS Admin" in frappe.get_roles(user):
#         return ""

#     # Get user's office (assumes a Link field "office" on User)
#     user_office = frappe.db.get_value("User", user, "organisation")
#     if not user_office:
#         # No office assigned → see nothing
#         return "1=0"

#     # Try to treat Office as a tree using lft/rgt (standard Frappe tree)
#     try:
#         office_doc = frappe.get_doc("Organisation", user_office)

#         # Get this office + all child offices
#         offices = frappe.get_all(
#             "Organisation",
#             filters={
#                 "lft": (">=", office_doc.lft),
#                 "rgt": ("<=", office_doc.rgt),
#             },
#             pluck="name",
#         )
#     except Exception:
#         # Fallback: if Office is not a tree or lft/rgt missing
#         offices = [user_office]

#     if not offices:
#         offices = [user_office]

#     # Safely escape office names for SQL
#     escaped_offices = ", ".join([frappe.db.escape(o) for o in offices])

#     # IMPORTANT: adjust fieldname "office" to your actual field on Claim
#     return f"`tabClaim`.`dispensary` in ({escaped_offices})"


def derive_action(prev, new):
        prev = (prev or "").strip()
        new = (new or "").strip()

        if not prev:
            return "Created"

        if prev in ["Returned", "Rejected"] and new not in [prev]:
            return "Re-submitted"
        if new == "Sanctioned":
            return "Sanctioned"
        if new == "Rejected":
            return "Rejected"
        if new == "Returned":
            return "Returned"

        return "Moved"


def get_child_organisations(root_office):
    """Return root_organisation + all its descendants using parent_organisation."""
    to_visit = [root_office]
    all_offices = set()
 
    while to_visit:
        current = to_visit.pop()
        if current in all_offices:
            continue
 
        all_offices.add(current)
 
        children = frappe.get_all(
            "Organisation",
            filters={"parent_organisation": current},
            pluck="name"
        )
        to_visit.extend(children)
 
    return list(all_offices)

# Show only claim authorised for the user to see in the CLAIM list view
def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user
 
    # Full access for Administrator (and optionally System Manager etc.)
    if user in ("Administrator"):
        return ""
 
    # If you have a special role that should see everything, uncomment:
    # if "MRCMS Admin" in frappe.get_roles(user):
    #     return ""
 
    # Get user's organisation
    user_authority = frappe.db.get_value("User", user, "authority")
 
    user_organisation, user_section = frappe.db.get_value("User", user,["organisation", "section"]) or (None, None)

    if not user_organisation:
        # No organisation assigned → see nothing
        return "1=0"

    organisations = get_child_organisations(user_organisation)
    if not organisations:
        organisations = [user_organisation]
 
    escaped_organisations = ", ".join(frappe.db.escape(o) for o in organisations)
    organisation_condition = f"`tabClaim`.`dispensary` in ({escaped_organisations})"

    # --- New IMO Role Restriction Logic ---
    user_roles = frappe.get_roles(user)
    # Check if the user is an IMO. If so, add the workflow state restriction.
    if "IMO" in user_roles:
        # The IMO should only see claims that are both in their organisation AND in 'IMO Review' state.
        workflow_condition = "`tabClaim`.`workflow_state` = 'IMO Review'"
        # Combine the two conditions using AND
        return f"({organisation_condition}) AND ({workflow_condition})"
    
    # --- Default: Apply only organisation Restriction for Non-IMOs (e.g., clerk, etc.) ---
    if not user_section:
        # If the user is not an IMO, only the organisation restriction applies (assuming this is the base requirement)
        return organisation_condition
    else:
        # If the user belongs to a section in the Directorate apply both org condition and Section/MRC region condition
        section_condition = ""
        # Get all districts that belong to this MRC Region
        districts_in_region = frappe.get_all("District", filters={"mrc_region": user_section}, pluck="name")
        if districts_in_region:
            escaped_districts = ", ".join(frappe.db.escape(d) for d in districts_in_region)
            section_condition = f"`tabClaim`.`district` in ({escaped_districts})"
        else:
            # If no districts match the section → show nothing
            section_condition = "1=0"

        # If the user has a section associated, then list only claims associtated with that section
        return f"({section_condition}) AND ({organisation_condition})"

@frappe.whitelist()
def get_required_documents(amount_claimed):
    if not amount_claimed:
        return []
 
    # 1️⃣ Determine category
    claim_category = get_claim_category_by_amount(amount_claimed)
 
    if not claim_category:
        frappe.throw("No Claim Category configured for this amount")
 
    # 2️⃣ Fetch active rules for category
    rules = frappe.get_all(
        "Claim Document Rule",
        filters={
            "claim_category": claim_category,
            "docstatus": 1
        },
        pluck="name"
    )
 
    documents = []
    added = set()
 
    for rule in rules:
        rule_doc = frappe.get_doc("Claim Document Rule", rule)
 
        for row in rule_doc.claim_document_rule_details:
            if row.claim_doc_master in added:
                continue
 
            documents.append({
                "claim_doc_master": row.claim_doc_master,
                "claim_doc_name": frappe.db.get_value(
                    "Claim Document Master",
                    row.claim_doc_master,
                    "document_name"
                ),
                "mandatory": "Yes"
            })
 
            added.add(row.claim_doc_master)
 
    return {
        "claim_category": claim_category,
        "documents": documents
    }

# def get_claim_category_from_amount(amount):
#     amount = float(amount or 0)
#     category = frappe.get_all(
#         "Claim Category",
#         filters={
#             "min_amount": ("<=", amount),
#             "max_amount": (">=", amount),
#         },
#         fields=["name"],
#         order_by="min_amount asc",
#         limit=1
#     )

#     return category[0].name if category else None

@frappe.whitelist()
def get_claim_category_by_amount(passed_amount):
    amount = float(passed_amount)
 
    categories = frappe.get_all(
        "Claim Category",
        fields=["name", "min_amount", "max_amount"],
        order_by="min_amount asc"  
    )
 
    for c in categories:
        min_val = float(c.min_amount or 0)
        max_val = float(c.max_amount or 0)
 
        if min_val <= amount <= max_val:
            return c.name
 
    return None

@frappe.whitelist()
def create_claim_bundle_management(claims_data=None):

    if not claims_data:
        frappe.throw("⚠️ No claims selected.")

    if isinstance(claims_data, str):
        claims_data = json.loads(claims_data)

    max_claims = frappe.db.get_single_value(
        "Mrcms Settings", "max_claims_per_bundle"
    ) or 5

    user_org, _ = frappe.db.get_value(
        "User",
        frappe.session.user,
        ["organisation", "section"]
    )

    created_bundles = []

    for claim in claims_data:
        claim_no = claim.get("claim_no")
        claim_category = claim.get("claim_category")
        district = claim.get("district")

        if not district:
            frappe.throw(f"District not found for Claim {claim_no}")

        # 🔹 Derive MRC Section from District
        mrc_section = frappe.db.get_value(
            "District",
            district,
            "mrc_region"
        )

        if not mrc_section:
            frappe.throw(
                f"MRC Section not mapped for District {district} (Claim {claim_no})"
            )

        # Skip if already bundled
        if frappe.db.exists("Claim Bundle Details", {"claim_no": claim_no}):
            continue

        # 🔹 Find open bundle by Org + MRC Section + Category
        open_bundle = frappe.get_all(
            "Claim Bundle Management",
            filters={
                "organisation": user_org,
                "section": mrc_section,
                "bundle_status": "Open",
                "claim_category": claim_category
            },
            order_by="creation desc",
            limit=1
        )

        cbm = None

        if open_bundle:
            cbm = frappe.get_doc("Claim Bundle Management", open_bundle[0].name)

            if len(cbm.details) >= max_claims:
                cbm.bundle_status = "Closed"
                cbm.save(ignore_permissions=True)
                cbm = None

        # 🔹 Create new bundle if required
        if not cbm:
            cbm = frappe.new_doc("Claim Bundle Management")
            cbm.organisation = user_org
            cbm.section = mrc_section
            cbm.claim_category = claim_category
            cbm.bundle_status = "Open"

        # 🔹 Add claim to bundle
        cbm.append("details", {
            "claim_no": claim_no,
            "claim_date": claim.get("claim_date"),
            "district": district,
            "ip_no": claim.get("ip_no"),
            "ip_name": claim.get("ip_name"),
            "name_of_patient": claim.get("name_of_patient"),
            "phone": claim.get("phone"),
            "dispensary": claim.get("dispensary"),
            "claim_status": claim.get("claim_status"),
            "amount_claimed": claim.get("amount_claimed"),
            "passed_amount": claim.get("passed_amount"),
            "ifs_code": claim.get("ifs_code"),
            "bank_account_no": claim.get("bank_account_no"),
            "bank_name": claim.get("bank_name")
        })

        if cbm.get("__islocal"):
            cbm.insert(ignore_permissions=True)
        else:
            cbm.save(ignore_permissions=True)

        created_bundles.append(cbm.name)

    frappe.db.commit()

    if created_bundles:
        bundle_list = "\n".join(sorted(set(created_bundles)))
        frappe.msgprint(
            f"✅ Claim Bundles created/updated successfully!\n\nBundle Numbers:\n{bundle_list}",
            indicator="green"
        )
    else:
        frappe.msgprint(
            "⚠️ No new claim bundles were created (all claims may already be bundled).",
            indicator="orange"
        )

from tqerp_mrcms.api import create_claim_bundle_management
 
def auto_add_claim_to_bundle(doc, method):
    """
    Automatically add a sanctioned claim to a Claim Bundle.
    Only for Category C1 and C2.
    """
 
    if doc.claim_status != "Sanctioned":
        return
 
    if doc.claim_category not in ["Category C1", "Category C2"]:
        return
 
    claim_data = [{
        "claim_no": doc.name,
        "claim_category": doc.claim_category,  # important for separate bundles
        "claim_date": doc.claim_date or "",
        "ip_no": doc.ip_no or "",
        "ip_name": doc.ip_name or "",
        "name_of_patient": doc.name_of_patient or "",
        "phone": doc.phone or "",
        "dispensary": doc.dispensary or "",
        "claim_status": doc.claim_status,
        "amount_claimed": doc.amount_claimed or 0,
        "passed_amount": doc.passed_amount or 0,
        "ifs_code": doc.ifs_code or "",
        "bank_account_no": doc.bank_account_no or "",
        "bank_name": doc.bank_name or ""
    }]
 
    create_claim_bundle_management(claims_data=claim_data)
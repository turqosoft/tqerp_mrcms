from frappe.model.document import Document
import frappe
from frappe.utils import now_datetime, nowdate
from frappe.utils import getdate, add_days
import os, urllib

class Claim(Document):

    def validate(self):
            self.validate_mandatory_documents()

            self.set_comment_meta()
            self.prevent_edit_others_comments()
    
            if not self.amount_claimed:
                return
    
            # ALWAYS derive category from amount
            new_category = get_claim_category_from_amount(self.amount_claimed)
    
            category_changed = self.claim_category != new_category
            self.claim_category = new_category
    
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
        self.log_claim_process("Created")
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
            self.validate_entitlement_period()
 
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

    # Fetch all entitlement periods for this IP
    def before_print(self, print_settings=None):
   
        entitlements = frappe.get_all(
            "Entitlement",
            filters={
                "parent": self.ip_no,
                "parenttype": "Insured Person"
            },
            fields=["start_date", "end_date"],
            order_by="start_date asc"  
        )
 
        if entitlements:
           
            periods = [
                f"{frappe.utils.formatdate(e.start_date, 'dd-mm-yyyy')} to {frappe.utils.formatdate(e.end_date, 'dd-mm-yyyy')}"
                for e in entitlements
            ]
            # Join multiple periods with line breaks for HTML
            self.entitled_periods = ",<br><br><br>".join(periods)
        else:
            self.entitled_periods = "--"
            
    def on_submit(self):
        """Log submission of the Claim"""
        self.log_claim_process("Submitted")
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


    def log_claim_process(self, action, user=None, organisation=None):
        """Append an entry to Claim Process child table with full name and authority"""
        from frappe.utils import now_datetime
 
        if not user:
            user = frappe.session.user
        if not organisation:
            organisation = frappe.db.get_value("User", user, "organisation")
 
        # Get user details
        user_doc = frappe.get_doc("User", user)
        full_name = user_doc.full_name or user
        authority = user_doc.authority or ""
 
        # Get last log entry for this Claim
        last_logs = frappe.get_all(
            "Claim Process",
            filters={"parent": self.name},
            fields=["name", "date"],
            order_by="date desc",
            limit_page_length=1,
        )
 
        now = now_datetime()
 
        if last_logs:
            last_modified = last_logs[0].get("date")
            last_log_name = last_logs[0].get("name")
 
            # Update duration for previous log if exists
            if last_modified and last_log_name:
                duration_secs = (now - last_modified).total_seconds()
                frappe.db.set_value(
                    "Claim Process",
                    last_log_name,
                    "duration_seconds",
                    duration_secs,
                )
 
        # Append entry to child table
        self.append("claim_process", {
            "user": user,
            "activity": action,
            "organisation": organisation,
            "user_full_name": full_name,
            "user_authority": authority,
            "date": now
        })
 
        # Optional: insert a separate doc if needed
        log = frappe.get_doc({
            "doctype": "Claim Process",
            "parent": self.name,
            "parentfield": "claim_process",
            "parenttype": "Claim",
            "user": user,
            "activity": action,
            "organisation": organisation,
            "user_full_name": full_name,
            "user_authority": authority,
            "date": now
        })
        log.insert(ignore_permissions=True)

    def log_claim_status_change(self, previous_doc):
        """Track changes to claim_status only"""
        if not previous_doc:
            return
 
        old_status = previous_doc.get("claim_status")
        new_status = self.get("claim_status")
 
        if old_status != new_status:
            # Fetch the organisation of the logged-in user
            organisation = frappe.db.get_value("User", frappe.session.user, "organisation") or "Not Set"
 
            # Log claim_status change with organisation
            self.log_claim_process(
                action=f'Claim status changed from "{old_status}" to "{new_status}"',
                user=frappe.session.user,
                organisation=organisation
            )

    def populate_required_documents(self):
        if not self.claim_category:
            return
 
        # Clear existing docs
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
 
                # 🔹 Fetch document name from master
                doc_name,is_mandatory = frappe.db.get_value(
                    "Claim Document Master",
                    r.claim_doc_master,
                     ["document_name", "is_mandatory"]
                )
 
                self.append("claim_required_documents", {
                    "claim_doc_master": r.claim_doc_master,
                    "claim_doc_name": doc_name,   # ✅ explicitly set
                    "mandatory": "Yes" if is_mandatory and is_mandatory.lower() == "yes" else "No"
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

    def validate_mandatory_documents(self):
        prev = self.get_doc_before_save()
 
        missing = []
        upload_happened = False
 
        for row in self.claim_required_documents:
            if row.mandatory == "Yes":
                # Check missing
                if not row.uploaded_file or not str(row.uploaded_file).strip():
                    missing.append(row.claim_doc_name or row.claim_doc_master)
 
            # Detect NEW upload in this save
            if prev:
                prev_row = next(
                    (r for r in prev.claim_required_documents
                    if r.name == row.name),
                    None
                )
                if prev_row:
                    if not prev_row.uploaded_file and row.uploaded_file:
                        upload_happened = True
            else:
                # New doc, first upload
                if row.uploaded_file:
                    upload_happened = True
 
        # BLOCK save if:
        # mandatory docs missing
        if missing and not upload_happened:
            frappe.throw(
                "Please upload all mandatory documents before saving or approving.<br><br>"
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

def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user
 
    # Full access for Administrator (and optionally System Manager etc.)
    if user in ("Administrator"):
        return ""
 
    # If you have a special role that should see everything, uncomment:
    # if "MRCMS Admin" in frappe.get_roles(user):
    #     return ""
 
    # Get user's organisation (adjust fieldname on User if different)
    user_organisation = frappe.db.get_value("User", user, "organisation")
    user_authority = frappe.db.get_value("User", user, "authority")
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
 
    # If the user is not an IMO, only the organisation restriction applies (assuming this is the base requirement)
    return f"`tabClaim`.`dispensary` in ({escaped_organisations})"

@frappe.whitelist()
def get_required_documents(amount_claimed):
    if not amount_claimed:
        return []
 
    # 1️⃣ Determine category
    claim_category = get_claim_category_from_amount(amount_claimed)
 
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

def get_claim_category_from_amount(amount):
    amount = float(amount or 0)
    category = frappe.get_all(
        "Claim Category",
        filters={
            "min_amount": ("<=", amount),
            "max_amount": (">=", amount),
        },
        fields=["name"],
        order_by="min_amount asc",
        limit=1
    )

    return category[0].name if category else None

@frappe.whitelist()
def create_claim_bundle_management(claims_data=None):
    import json
    import frappe
 
    if not claims_data:
        frappe.throw("⚠️ No claims selected.")
 
    if isinstance(claims_data, str):
        claims_data = json.loads(claims_data)
 
    max_claims = frappe.db.get_single_value("Mrcms Settings", "max_claims_per_bundle") or 5
    user_org = frappe.db.get_value("User", frappe.session.user, "organisation")
 
    created_bundles = []
 
    for claim in claims_data:
        claim_no = claim.get("claim_no")
        claim_category = claim.get("claim_category")
 
        # Skip if already bundled
        if frappe.db.exists("Claim Bundle Details", {"claim_no": claim_no}):
            continue
 
        # Find the latest open bundle for this category
        open_bundle = frappe.get_all(
            "Claim Bundle Management",
            filters={
                "organisation": user_org,
                "bundle_status": "Open",
                "claim_category": claim_category
            },
            order_by="creation desc",
            limit=1
        )
 
        if open_bundle:
            cbm = frappe.get_doc("Claim Bundle Management", open_bundle[0].name)
            # Check if bundle reached max_claims
            if len(cbm.details) >= max_claims:
                cbm.bundle_status = "Closed"
                cbm.save(ignore_permissions=True)
                cbm = None
        else:
            cbm = None
 
        # If no valid open bundle, create new one
        if not cbm:
            cbm = frappe.new_doc("Claim Bundle Management")
            cbm.organisation = user_org
            cbm.bundle_status = "Open"
            cbm.claim_category = claim_category
 
        # Add claim to bundle
        cbm.append("details", {
            "claim_no": claim_no,
            "claim_date": claim.get("claim_date"),
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
 
        # Save existing bundle instead of insert
        if cbm.get("__islocal"):
            cbm.insert(ignore_permissions=True)  # only insert if new
        else:
            cbm.save(ignore_permissions=True)    # update existing
 
        created_bundles.append(cbm.name)
 
    frappe.db.commit()
 
    if created_bundles:
        bundle_list = "\n".join(list(set(created_bundles)))
        frappe.msgprint(
            f"✅ Claim Bundles created/updated successfully!\n\nBundle Numbers:\n{bundle_list}",
            indicator="green"
        )
        frappe.logger().info(f"Claim Bundles created/updated: {created_bundles}")
    else:
        frappe.msgprint(
            "⚠️ No new claim bundles were created (all claims may already be bundled).",
            indicator="orange"
        )
 
 
 
 
import frappe
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
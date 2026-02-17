import frappe
from frappe.model.document import Document
from tqerp_mrcms.api import update_bundle_status


class ClaimPaymentList(Document):

    def before_submit(self):
        # Capture submitting user
        if not self.submitted_by:
            self.submitted_by = frappe.session.user

        user = frappe.get_doc("User", self.submitted_by)
        self.submitted_by_name = user.full_name
        self.submitted_by_authority = user.authority

    # --------------------------------------------------
    # BEFORE INSERT
    # --------------------------------------------------
    def before_insert(self):
        """
        Allow only:
        - Unlinked claims
        - Claims already linked to THIS CPL
        Block claims linked to OTHER CPLs
        """
        valid_rows = []
        skipped_claims = []

        for row in self.details:
            if not row.claim_no:
                continue

            existing_pl = frappe.db.get_value(
                "Claim", row.claim_no, "claim_payment_list"
            )

            if existing_pl and existing_pl != self.name:
                skipped_claims.append(
                    f"{row.claim_no} (already in {existing_pl})"
                )
            else:
                valid_rows.append(row)

        if not valid_rows:
            frappe.throw(
                "❌ All selected claims are already linked to other Claim Payment Lists:<br><br>"
                + "<br>".join(skipped_claims)
            )

        # if skipped_claims:
        #     frappe.msgprint(
        #         "⚠️ These claims were skipped because they are already linked to other CPLs:<br><br>"
        #         + "<br>".join(skipped_claims),
        #         indicator="orange",
        #         title="Skipped Claims"
        #     )

        self.details = valid_rows

    def before_save(self):
 
        from tqerp_mrcms.api import reverse_fund_on_cancel
 
        # --------------------------------------------------
        # 1️⃣ Refund old fund if fund manager changed (EDIT ONLY)
        # --------------------------------------------------
        if not self.is_new():
 
            old_fund = frappe.db.get_value(
                self.doctype,
                self.name,
                "fund_manager"
            )
 
            if old_fund and old_fund != self.fund_manager:
                reverse_fund_on_cancel(
                    name=self.name,
                    doctype=self.doctype
                )
 
        # --------------------------------------------------
        # 2️⃣ CLAIM PAYMENT LIST LINK SYNC (NEW + EDIT)
        # --------------------------------------------------
 
        # Get old child claims (only if document already exists)
        old_claims = set()
 
        if not self.is_new():
            old_rows = frappe.get_all(
                "Claim Payment Details",  # ⚠ Replace if different
                filters={"parent": self.name},
                pluck="claim_no"
            )
            old_claims = set(old_rows)
 
        # Current UI claims
        current_claims = {
            row.claim_no for row in self.details if row.claim_no
        }
 
        # Claims removed from UI
        removed_claims = old_claims - current_claims
 
        # Claims newly added
        added_claims = current_claims - old_claims
 
        # --------------------------------------------------
        # 3️⃣ CLEAR REMOVED CLAIM LINKS
        # --------------------------------------------------
        for claim_no in removed_claims:
 
            current_link = frappe.db.get_value(
                "Claim",
                claim_no,
                "claim_payment_list"
            )
 
            # Only clear if linked to THIS CPL
            if current_link == self.name:
                frappe.db.set_value(
                    "Claim",
                    claim_no,
                    "claim_payment_list",
                    None,
                    update_modified=False
                )
 
        # --------------------------------------------------
        # 4️⃣ LINK ADDED CLAIMS
        # --------------------------------------------------
        for claim_no in added_claims:
 
            existing_link = frappe.db.get_value(
                "Claim",
                claim_no,
                "claim_payment_list"
            )
 
            # Do not override another CPL
            if existing_link and existing_link != self.name:
                continue
 
            frappe.db.set_value(
                "Claim",
                claim_no,
                "claim_payment_list",
                self.name,
                update_modified=False
            )


    # --------------------------------------------------
    # ON UPDATE claim bundle-claim payment link
    # --------------------------------------------------
    # def before_save(self):
    def on_update(self):
        #  Prevent recursion in same request
        if frappe.flags.get("in_cpl_before_save"):
            return

        frappe.flags.in_cpl_before_save = True

        try:
            if self.is_new():
                return

            affected_bundles = set()
            browser_messages = []

            # --------------------------------------------------
            # CLAIMS CURRENTLY LINKED TO THIS CPL (DB STATE)
            # --------------------------------------------------
            db_claims = set(
                frappe.get_all(
                    "Claim",
                    filters={"claim_payment_list": self.name},
                    pluck="name"
                )
            )

            ui_claims = {r.claim_no for r in self.details if r.claim_no}

            # --------------------------------------------------
            # REMOVED CLAIMS (UI → DB DIFF)
            # --------------------------------------------------
            for claim_no in db_claims - ui_claims:

                # Clear Claim master link
                frappe.db.set_value(
                    "Claim",
                    claim_no,
                    "claim_payment_list",
                    None,
                    update_modified=False
                )

                # Clear ONLY rows linked to THIS CPL
                child_rows = frappe.get_all(
                    "Claim Bundle Details",
                    filters={
                        "claim_no": claim_no,
                        "claim_payment_list": self.name,
                        "parenttype": "Claim Bundle Management"
                    },
                    fields=["name", "parent"]
                )

                for r in child_rows:
                    frappe.db.set_value(
                        "Claim Bundle Details",
                        r.name,
                        "claim_payment_list",
                        None,
                        update_modified=False
                    )

                    affected_bundles.add(r.parent)

                    # browser_messages.append(
                    #     f"❌ Claim <b>{claim_no}</b> unlinked from "
                    #     f"Claim Payment List <b>{self.name}</b>"
                    # )

            # --------------------------------------------------
            # ADD / UPDATE CLAIMS FROM UI
            # --------------------------------------------------
            for row in self.details:
                if not row.claim_no or not row.claim_bundle_no:
                    continue

                # Current CPL on Claim 
                existing_pl = frappe.db.get_value(
                    "Claim",
                    row.claim_no,
                    "claim_payment_list"
                )

                #  Never override another CPL
                if existing_pl and existing_pl != self.name:
                    continue

                # Link Claim → CPL if unlinked
                if not existing_pl:
                    frappe.db.set_value(
                        "Claim",
                        row.claim_no,
                        "claim_payment_list",
                        self.name,
                        update_modified=False
                    )

                # Fetch EXACT bundle child row
                child_row = frappe.db.get_value(
                    "Claim Bundle Details",
                    {
                        "claim_no": row.claim_no,
                        "parent": row.claim_bundle_no,
                        "parenttype": "Claim Bundle Management"
                    },
                    ["name", "claim_payment_list"],
                    as_dict=True
                )

                if not child_row:
                    continue

                old_pl = child_row.claim_payment_list

                
                if old_pl != self.name:
                    frappe.db.set_value(
                        "Claim Bundle Details",
                        child_row.name,
                        "claim_payment_list",
                        self.name,
                        update_modified=False
                    )

                    # browser_messages.append(
                    #     f" Claim <b>{row.claim_no}</b> linked to "
                    #     f"Claim Payment List <b>{self.name}</b>"
                    # )

                    affected_bundles.add(row.claim_bundle_no)

            # --------------------------------------------------
            # UPDATE BUNDLE STATUS 
            # --------------------------------------------------
            for bundle in affected_bundles:
                update_bundle_status(bundle)

            # --------------------------------------------------
            # SHOW BROWSER MESSAGE (ONCE)
            # --------------------------------------------------
            if browser_messages:
                frappe.msgprint(
                    "<br>".join(browser_messages),
                    title="Claim Payment List Changes",
                    indicator="green"
                )

        finally:
            frappe.flags.in_cpl_before_save = False



   # --------------------------------------------------
    # ON TRASH
    # --------------------------------------------------
    def on_trash(self):
        from tqerp_mrcms.api import reverse_fund_on_cancel

        # 1️⃣ Reverse allocated fund
        reverse_fund_on_cancel(name=self.name, doctype=self.doctype)

        # 2️⃣ Clear CPL link from Claims
        for row in self.details:
            if not row.claim_no:
                continue

            current_link = frappe.db.get_value(
                "Claim", row.claim_no, "claim_payment_list"
            )

            # Only unlink if THIS CPL set it
            if current_link == self.name:
                frappe.db.set_value(
                    "Claim",
                    row.claim_no,
                    "claim_payment_list",
                    None
                )


    # --------------------------------------------------
    # VALIDATE
    # --------------------------------------------------
    def validate(self):
        seen = set()

        for row in self.details:
            if not row.claim_no:
                continue

            if row.claim_no in seen:
                frappe.throw(
                    f"❌ Claim <b>{row.claim_no}</b> is duplicated in this Claim Payment List."
                )

            seen.add(row.claim_no)

        if not self.details:
            frappe.throw(
                "⚠️ At least one Claim is required to save the Claim Payment List."
            )

      # ✅ FINAL authority for totals
        self.payment_total = sum(
            (row.passed_amount or 0) for row in self.details
        )  

        self.total_allocated = sum(
            (row.passed_amount or 0) for row in self.details
        )  


    

       

    # def on_cancel(self):
    #     from tqerp_mrcms.api import reverse_fund_on_cancel
    #     reverse_fund_on_cancel(self.name)

    #      # Clear bundle number from Claim
    #     for row in self.details:
    #         if row.claim_no:
    #             frappe.db.set_value(
    #                 "Claim",
    #                 row.claim_no,
    #                 "claim_payment_list",
    #                 None
    #             )


def get_child_organisations(root_office):
    """Return root_office + all its descendants using parent_organisation."""
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


def get_permission_query_conditions(user, doctype=None):
    if not user:
        user = frappe.session.user

    # Admin sees everything
    if user == "Administrator":
        return ""

    user_org, user_section = frappe.db.get_value(
        "User", user, ["organisation", "section"]
    ) or (None, None)

    if not user_org:
        return "1=0"

    organisations = get_child_organisations(user_org) or [user_org]
    escaped_orgs = ", ".join(frappe.db.escape(o) for o in organisations)

    org_condition = (
        "`tabClaim Payment List`.`organisation` "
        f"IN ({escaped_orgs})"
    )

    if not user_section:
        return org_condition

    section_condition = (
        "`tabClaim Payment List`.`section` = "
        f"{frappe.db.escape(user_section)}"
    )

    return f"({org_condition}) AND ({section_condition})"

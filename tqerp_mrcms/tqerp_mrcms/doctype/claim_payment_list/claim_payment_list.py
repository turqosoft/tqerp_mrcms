import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from tqerp_mrcms.api import update_bundle_status


class ClaimPaymentList(Document):

    def before_submit(self):
        # Capture submitting user
        if not self.submitted_by:
            self.submitted_by = frappe.session.user

        user = frappe.get_doc("User", self.submitted_by)
        self.submitted_by_name = user.full_name
        self.submitted_by_authority = user.authority





    def before_save(self):
        # Get current claim numbers from child table
        current_rows = [row for row in self.details if row.claim_no]

        current_claims = [row.claim_no for row in current_rows]

        # Get all Claims that were previously linked to this CPL
        previous_claims = frappe.get_all(
            "Claim",
            filters={"claim_payment_list": self.name},
            fields=["name"]
        )

        # -------------------------------
        # Remove CPL link from Claims that were deleted
        # -------------------------------
        for claim in previous_claims:
            if claim.name not in current_claims:
                # Clear link from Claim
                frappe.db.set_value("Claim", claim.name, "claim_payment_list", None)

                # Also clear link in Claim Bundle Details
                rows = frappe.get_all(
                    "Claim Bundle Details",
                    filters={"claim_no": claim.name},
                    fields=["parent"]
                )
                for r in rows:
                    frappe.db.set_value(
                        "Claim Bundle Details",
                        {
                            "parent": r.parent,
                            "parenttype": "Claim Bundle Management",
                            "claim_no": claim.name
                        },
                        "claim_payment_list",
                        None
                    )
                    # Optional: update bundle status
                    update_bundle_status(r.parent)

        # -------------------------------
        # Update CPL link for all current rows
        # -------------------------------
        for row in current_rows:
            if row.claim_no:
                # Update Claim
                frappe.db.set_value("Claim", row.claim_no, "claim_payment_list", self.name)

                # Update Claim Bundle Details
                if row.claim_bundle_no:
                    frappe.db.set_value(
                        "Claim Bundle Details",
                        {
                            "parent": row.claim_bundle_no,
                            "parenttype": "Claim Bundle Management",
                            "claim_no": row.claim_no
                        },
                        "claim_payment_list",
                        self.name
                    )
                    update_bundle_status(row.claim_bundle_no)


                
    def on_trash(self):
        """
        Clear claim_bundle_management link from Claim
        when this document is deleted.
        """
        for row in self.details:
            if row.claim_no:
                frappe.db.set_value(
                    "Claim",
                    row.claim_no,
                    "claim_payment_list",
                    None
                )

    def validate(self):
        """
        Validate the Claim Payment List:
        1. Prevent duplicate claims in the same Payment List.
        2. Optional: check that passed amounts or other fields are correct.
        """
        seen = set()
        for row in self.details:
            if not row.claim_no:
                continue

            # Prevent duplicate claim in same document
            if row.claim_no in seen:
                frappe.throw(f"❌ Claim {row.claim_no} is duplicated in the Payment List.")
            seen.add(row.claim_no)

        # Optional: other validations (e.g., total passed amount, fund checks, etc.)
        if not self.details:
            frappe.throw("⚠️ No valid Claims available to save in this Payment List.")

    def before_insert(self):
        # Filter out rows already linked to another Payment List
        valid_rows = []
        for row in self.details:
            if not row.claim_no:
                continue
            existing_pl = frappe.db.get_value("Claim", row.claim_no, "claim_payment_list")
            if existing_pl:
                frappe.msgprint(
                    f"⚠️ Claim {row.claim_no} is already linked to "
                    f"Claim Payment List <b>{existing_pl}</b> and will be skipped.",
                    title="Skipped Claim",
                    indicator="orange"
                )
            else:
                valid_rows.append(row)

        # Replace child table with only valid rows
        self.details = valid_rows


        


    # def on_submit(self):
    #     # Store bundle number in each Claim
    #     for row in self.details:   
    #         if row.claim_no:
    #             frappe.db.set_value(
    #                 "Claim",
    #                 row.claim_no,
    #                 "claim_payment_list",
    #                 self.name
    #             )


       

    def on_cancel(self):
        from tqerp_mrcms.api import reverse_fund_on_cancel
        reverse_fund_on_cancel(self.name)

         # Clear bundle number from Claim
        for row in self.details:
            if row.claim_no:
                frappe.db.set_value(
                    "Claim",
                    row.claim_no,
                    "claim_payment_list",
                    None
                )


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

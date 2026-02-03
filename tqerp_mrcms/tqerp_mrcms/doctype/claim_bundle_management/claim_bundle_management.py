import frappe
from frappe.model.document import Document

class ClaimBundleManagement(Document):

    def before_submit(self):
        if not self.submitted_by:
            self.submitted_by = frappe.session.user

        user = frappe.get_doc("User", self.submitted_by)

        self.submitted_by_name = user.full_name
        self.submitted_by_authority = user.authority

    def validate(self):
        """
        Prevent adding a claim to this bundle if it is already in:
        - Another Claim Bundle
        - Or in Claim Proceedings
        """
        for row in self.details:
            if not row.claim_no:
                continue
 
            # Check if claim is already in another Claim Bundle
            existing_bundle = frappe.db.get_value(
                "Claim",
                row.claim_no,
                "claim_bundle_management"
            )
            if existing_bundle and existing_bundle != self.name:
                frappe.throw(
                    f"❌ Claim {row.claim_no} is already linked to "
                    f"Claim Bundle {existing_bundle}. You cannot add it again."
                )
 
            # Check if claim is in any Claim Proceedings
            proceedings = frappe.db.get_value(
                "Claim",
                row.claim_no,
                "claim_proceedings"
            )
            if proceedings:
                frappe.throw(
                    f"❌ Claim {row.claim_no} is already linked to "
                    f"Claim Proceedings {proceedings}. You cannot add it to a bundle."
                )

            if self.workflow_state != "Draft":
                self.bundle_status = "Closed"

    def before_save(self):
        # Store bundle number in each Claim
        for row in self.details:  
            if row.claim_no:
                frappe.db.set_value(
                    "Claim",
                    row.claim_no,
                    "claim_bundle_management",
                    self.name
                )

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
                    "claim_bundle_management",
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

    # Organisation + child orgs
    organisations = get_child_organisations(user_org) or [user_org]
    escaped_orgs = ", ".join(frappe.db.escape(o) for o in organisations)

    org_condition = (
        "`tabClaim Bundle Management`.`organisation` "
        f"IN ({escaped_orgs})"
    )

    # If no section assigned → org-level access
    if not user_section:
        return org_condition

    # Section-level access
    section_condition = (
        "`tabClaim Bundle Management`.`section` = "
        f"{frappe.db.escape(user_section)}"
    )

    return f"({org_condition}) AND ({section_condition})"

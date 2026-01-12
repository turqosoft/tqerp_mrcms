import frappe
from frappe.model.document import Document


class ClaimPaymentList(Document):

    def before_submit(self):
        # Capture submitting user
        if not self.submitted_by:
            self.submitted_by = frappe.session.user

        user = frappe.get_doc("User", self.submitted_by)

        self.submitted_by_name = user.full_name
        self.submitted_by_authority = user.authority

    def on_cancel(self):
        from tqerp_mrcms.api import reverse_fund_on_cancel
        reverse_fund_on_cancel(self.name)


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
        "`tabClaim Payment List`.`organisation` "
        f"IN ({escaped_orgs})"
    )

    # If no section assigned → org-level access
    if not user_section:
        return org_condition

    # Section-level access
    section_condition = (
        "`tabClaim Payment List`.`section` = "
        f"{frappe.db.escape(user_section)}"
    )

    return f"({org_condition}) AND ({section_condition})"

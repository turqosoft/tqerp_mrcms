# Copyright (c) 2025, turqosoft and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

class ClaimProceedings(Document):
    def after_insert(self):
        """Log creation of a new Claim"""
        # Optional: You may still log creation if needed
        pass

    def on_cancel(self):
        if not self.fund_manager or not self.total_allocated:
            return
 
        frappe.get_attr("tqerp_mrcms.api.reverse_fund_on_cancel")(
            self.name,
            doctype="Claim Proceedings"
        )
        
def get_child_offices(root_office):
    """Return root_office + all its descendants using parent_office."""
    to_visit = [root_office]
    all_offices = set()

    while to_visit:
        current = to_visit.pop()
        if current in all_offices:
            continue

        all_offices.add(current)

        children = frappe.get_all(
            "Office",
            filters={"parent_office": current},
            pluck="name"
        )
        to_visit.extend(children)

    return list(all_offices)

def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    # Full access for Administrator (and optionally System Manager etc.)
    if user in ("Administrator", "Guest"):
        return ""

    # If you have a special role that should see everything, uncomment:
    # if "MRCMS Admin" in frappe.get_roles(user):
    #     return ""

    # Get user's office (adjust fieldname on User if different)
    user_office = frappe.db.get_value("User", user, "office")
    if not user_office:
        # No office assigned → see nothing
        return "1=0"

    offices = get_child_offices(user_office)
    if not offices:
        offices = [user_office]

    escaped_offices = ", ".join(frappe.db.escape(o) for o in offices)

    # IMPORTANT: adjust `office` to your actual Link field on Claim
    # e.g. `dispensary_office` or `assigned_office`
    return f"`tabClaim Proceedings`.`office` in ({escaped_offices})"


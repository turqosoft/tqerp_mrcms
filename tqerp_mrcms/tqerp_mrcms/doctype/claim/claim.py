from frappe.model.document import Document
import frappe
from frappe.utils import now_datetime

class Claim(Document):

    def after_insert(self):
        """Log creation of a new Claim"""
        # Optional: You may still log creation if needed
        # self.log_claim_process("Created")


    def on_update(self):
        self.log_claim_process("Created")

    def before_save(self):
        """Log changes to claim_status only"""
        previous_doc = self.get_doc_before_save()
        # self.log_claim_status_change(previous_doc)

    def on_submit(self):
        """Log submission of the Claim"""
        self.log_claim_process("Submitted")

    def log_claim_process(self, action, user=None, office=None):
        """Append an entry to Claim Process child table"""
        if not user:
            user = frappe.session.user
        if not office:
            office = frappe.db.get_value("User", user, "office")



        # Get last log entry for this Claim
        last_logs = frappe.get_all(
            "Claim Process",
            filters={"parent": self.name},
            fields=["name", "date"],
            order_by="date desc",
            limit_page_length=1,
        )

        if last_logs:
            last_modified= last_logs[0].get("date")
            last_log_name = last_logs[0].get("name")

            now = now_datetime()
            # Update duration for previous log if exists
            if last_modified and last_log_name:
                duration_secs = (now - last_modified).total_seconds()
                frappe.db.set_value(
                    "Claim Process",
                    last_log_name,
                    "duration_seconds",
                    duration_secs,
                )

        # Append entry
        self.append("claim_process", {
            "user": user,
            "activity": action,
            "office": office,  # Make sure this field exists in child table
            "date": now_datetime()
        })

        log = frappe.get_doc({
            "doctype": "Claim Process",
            "parent": self.name,
            "parentfield": "claim_process",
            "parenttype": "Claim",
            "user": user,
            "activity": action,
            "office": office,  # Make sure this field exists in child table
            "date": now_datetime()
        })
        log.insert(ignore_permissions=True)

    def log_claim_status_change(self, previous_doc):
        """Track changes to claim_status only"""
        if not previous_doc:
            return

        old_status = previous_doc.get("claim_status")
        new_status = self.get("claim_status")

        if old_status != new_status:
            # Fetch the office of the logged-in user
            office = frappe.db.get_value("User", frappe.session.user, "office") or "Not Set"

            # Log claim_status change with office
            self.log_claim_process(
                action=f'Claim status changed from "{old_status}" to "{new_status}"',
                user=frappe.session.user,
                office=office
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
#     user_office = frappe.db.get_value("User", user, "office")
#     if not user_office:
#         # No office assigned → see nothing
#         return "1=0"

#     # Try to treat Office as a tree using lft/rgt (standard Frappe tree)
#     try:
#         office_doc = frappe.get_doc("Office", user_office)

#         # Get this office + all child offices
#         offices = frappe.get_all(
#             "Office",
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
    if user in ("Administrator"):
        return ""

    # If you have a special role that should see everything, uncomment:
    # if "MRCMS Admin" in frappe.get_roles(user):
    #     return ""

    # Get user's office (adjust fieldname on User if different)
    user_office = frappe.db.get_value("User", user, "office")
    user_authority = frappe.db.get_value("User", user, "authority")
    if not user_office:
        # No office assigned → see nothing
        return "1=0"

    offices = get_child_offices(user_office)
    if not offices:
        offices = [user_office]

    escaped_offices = ", ".join(frappe.db.escape(o) for o in offices)
    
    office_condition = f"`tabClaim`.`dispensary` in ({escaped_offices})"
    
    # --- New IMO Role Restriction Logic ---
    user_roles = frappe.get_roles(user)
    
    # Check if the user is an IMO. If so, add the workflow state restriction.
    if "IMO" in user_roles:
        # The IMO should only see claims that are both in their office AND in 'IMO Review' state.
        workflow_condition = "`tabClaim`.`workflow_state` = 'IMO Review'"
        
        # Combine the two conditions using AND
        return f"({office_condition}) AND ({workflow_condition})"

    # --- Default: Apply only Office Restriction for Non-IMOs (e.g., clerk, etc.) ---

    # If the user is not an IMO, only the office restriction applies (assuming this is the base requirement)
    return f"`tabClaim`.`dispensary` in ({escaped_offices})"

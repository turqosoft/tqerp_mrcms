import frappe
from frappe.utils import now_datetime
from frappe.model.document import Document

class ClaimBundleManagement(Document):
	pass
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
		user_org = frappe.db.get_value("User", user, "organisation")
		if not user_org:
			# No organisation assigned → see nothing
			return "1=0"

		organisations = get_child_organisations(user_org)
		if not organisations:
			organisations = [user_org]

		escaped_orgs = ", ".join(frappe.db.escape(o) for o in organisations)

		return f"`tabClaim Bundle Management`.`organisation` in ({escaped_orgs})"

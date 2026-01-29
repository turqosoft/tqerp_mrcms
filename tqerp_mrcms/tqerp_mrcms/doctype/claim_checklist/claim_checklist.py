import frappe
from frappe.model.document import Document

class ClaimChecklist(Document):
	def validate(self):
			# prevent duplicate based on combination:
			# type + hospital_type
			if frappe.db.exists(
				"Claim Checklist",
				{
					"type": self.type,
					"hospital_type": self.hospital_type,
					"name": ["!=", self.name]
				}
			):
				frappe.throw(
					f"Record already exists for "
					f"Type '{self.type}' and Hospital Type '{self.hospital_type}'"
				)
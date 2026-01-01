# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class ClaimCategory(Document):
	def validate(self):
		min_amount = float(self.min_amount or 0)
		max_amount = float(self.max_amount or 0)

		if min_amount > max_amount:
			frappe.throw(_("Min Amount cannot be greater than Max Amount"))

		overlapping = frappe.db.sql("""
			SELECT name
			FROM `tabClaim Category`
			WHERE name != %s
			AND (
					(%s BETWEEN min_amount AND max_amount)
				OR (%s BETWEEN min_amount AND max_amount)
				OR (min_amount BETWEEN %s AND %s)
			)
		""", (
			self.name,
			min_amount,
			max_amount,
			min_amount,
			max_amount
		), as_dict=True)

		if overlapping:
			frappe.throw(
				_("Amount range overlaps with existing Claim Category: {0}")
				.format(overlapping[0].name)
			)

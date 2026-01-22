# Copyright (c) 2024, Rosh R and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class InsuredPerson(Document):

    def validate(self):
        self.add_self_to_family_members()

    def add_self_to_family_members(self):
        """
        Auto add / update insured person as 'Self' in Family Members table
        """

        self_row = None

        # Find existing 'Self' row
        for row in self.family_members:
            if row.relation == "Self":
                self_row = row
                break

        if self_row:
            # Update existing row
            self_row.member_name = self.ip_name
            self_row.gender = self.gender
            self_row.dob = self.dob
        else:
            # Add new Self row
            self.append("family_members", {
                "member_name": self.ip_name,
                "gender": self.gender,
                "relation": "Self",
                "dob": self.dob
            })

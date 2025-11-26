from frappe.model.document import Document
import frappe
from frappe.utils import now_datetime

class Claim(Document):

    def after_insert(self):
        """Log creation of a new Claim"""
        self.log_claim_process("Created")

    def before_save(self):
        """Log Save + Field Changes"""
        previous_doc = self.get_doc_before_save()

        # If NOT a new doc → add "Saved"
        if previous_doc:
            self.log_claim_process("Saved")

        # Also log all field changes
        self.log_all_field_changes(previous_doc)

    def on_submit(self):
        """Log submission of the Claim"""
        self.log_claim_process("Submitted")

    def log_claim_process(self, action):
        """Append an entry to Claim Process child table"""
        self.append("claim_process", {
            "user": frappe.session.user,
            "activity": action,
            "date": now_datetime()
        })

    def log_all_field_changes(self, previous_doc):
        """Log changes for every field except child tables and layout fields"""

        if not previous_doc:
            return  # No previous version → no change tracking

        for field in self.meta.fields:
            fieldname = field.fieldname

            # Skip child tables and layout fields
            if field.fieldtype in ["Table", "Column Break", "Section Break", "Button", "HTML"]:
                continue

            old_val = previous_doc.get(fieldname)
            new_val = self.get(fieldname)

            if old_val != new_val:
                self.append("claim_process", {
                    "user": frappe.session.user,
                    "activity": f'Field "{field.label}" changed from "{old_val}" to "{new_val}"',
                    "date": now_datetime()
                })

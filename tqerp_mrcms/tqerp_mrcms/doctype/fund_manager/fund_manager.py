
import frappe
from frappe.utils import nowdate, now_datetime
from frappe.model.document import Document

class FundManager(Document):
    pass  # The class itself can remain empty

def create_opening_entries(doc, method):
    """
    Handles Fund Utilization Entries for Fund Manager.

    1.On submit (docstatus==1):
        - Creates opening Fund Utilization Entries for each row in Fund Manager Details.
        - Skips if an opening entry already exists.

    2. On cancel (docstatus==2):
        - Marks all related Fund Utilization Entries as cancelled.
        - Resets allocated, paid, and balance amounts in the Fund Manager child rows.
        - Does NOT save the Fund Manager itself (cannot save a cancelled document).
    """
    for row in doc.details:  # child table fieldname is 'details'
        # === Handle cancellation ===
        if doc.docstatus == 2:  # Cancelled
            # Fetch all non-cancelled Fund Utilization Entries for this row
            entries = frappe.get_all(
                "Fund Utilization Entry",
                filters={
                    "fund_id": doc.name,
                    "organisation": row.organisation,
                    "is_cancelled": 0
                }
            )

            # Mark each ledger entry as cancelled
            for e in entries:
                entry_doc = frappe.get_doc("Fund Utilization Entry", e.name)
                entry_doc.is_cancelled = 1
                entry_doc.save(ignore_permissions=True)

            # Reset Fund Manager child row amounts (in memory only)
            row.allocated = 0
            row.paid = 0
            row.balance = row.fixed or 0

            continue  # Skip creating a new entry for cancelled Fund Manager

        # === Handle submission ===
        # Skip creating opening entry if it already exists
        exists = frappe.db.exists("Fund Utilization Entry", {
            "fund_id": doc.name,
            "organisation": row.organisation,
            "voucher_no": doc.name,
            "transaction_type": "Opening"
        })
        if exists:
            continue

        # Create opening ledger entry
        frappe.get_doc({
            "doctype": "Fund Utilization Entry",
            "fund_id": doc.name,
            "organisation": row.organisation,
            "posting_date": nowdate(),
            "posting_datetime": now_datetime(),
            "transaction_type": "Opening",
            "voucher_type": "Fund Manager",
            "voucher_no": doc.name,
            "debit": row.fixed or 0,
            "credit": 0,
            "balance": row.fixed or 0,
            "remarks": f"Opening entry for Fund Manager {doc.name}"
        }).insert(ignore_permissions=True)

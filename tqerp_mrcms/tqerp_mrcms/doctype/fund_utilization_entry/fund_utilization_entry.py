# Copyright (c) 2025, Turqosoft Solutions Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import nowdate, now_datetime
from frappe.model.document import Document


class FundUtilizationEntry(Document):
    pass



def create_utilization_entry(doc, method):
    """
    Auto-create Fund Utilization Entry when Claim Proceedings or Claim Payment List is saved.
    Uses doc.total_allocated as the amount to debit from fund.
    Cancels old ledger if fund or allocation changes, then creates a new entry.
    """

    if not getattr(doc, "fund_manager", None):
        return  # No fund selected

    # ==========================
    # CANCEL LOGIC (ADD THIS)
    # ==========================
    if doc.docstatus == 2:  # If document is Cancelled
 
        entries = frappe.get_all(
            "Fund Utilization Entry",
            filters={
                "voucher_no": doc.name,
                "transaction_type": "Utilization",
                "is_cancelled": 0
            }
        )
 
        for e in entries:
            old_entry = frappe.get_doc("Fund Utilization Entry", e.name)
            old_entry.is_cancelled = 1
            old_entry.save(ignore_permissions=True)
 
            # Reverse allocation from Fund Manager
            old_fund_doc = frappe.get_doc("Fund Manager", old_entry.fund_id)
            for row in old_fund_doc.details:
                if row.organisation == old_entry.organisation:
                    row.allocated = max(
                        0,
                        float(row.allocated or 0) - float(old_entry.credit or 0)
                    )
                    break
 
            old_fund_doc.save(ignore_permissions=True)
 
        return

    allocated_amount = float(getattr(doc, "total_allocated", 0) or 0)
    if allocated_amount <= 0:
        return  # Nothing to allocate

    # Step 1: Cancel old ledger entry if it exists
    existing_entry = frappe.get_all(
        "Fund Utilization Entry",
        filters={
            "voucher_no": doc.name,
            "transaction_type": "Utilization",
            "is_cancelled": 0
        },
        limit=1
    )

    if existing_entry:
        old_entry = frappe.get_doc("Fund Utilization Entry", existing_entry[0].name)
        old_entry.is_cancelled = 1
        old_entry.save(ignore_permissions=True)

        # Reverse allocation from old fund
        old_fund_doc = frappe.get_doc("Fund Manager", old_entry.fund_id)
        for row in old_fund_doc.details:
            if row.organisation == old_entry.organisation:
                row.allocated = max(0, float(row.allocated or 0) - float(old_entry.credit or 0))
                break
        old_fund_doc.save(ignore_permissions=True)

    # Step 2: Fetch Fund Manager Details for current fund
    fund_doc = frappe.get_doc("Fund Manager", doc.fund_manager)
    fm_row = None
    for row in fund_doc.details:
        if row.organisation == doc.organisation:
            fm_row = row
            break

    if not fm_row:
        frappe.throw(f"No Fund Manager Details found for {doc.organisation} in {doc.fund_manager}")

    # Convert string fields to float for calculations
    fixed = float(fm_row.fixed or 0)
    allocated = float(fm_row.allocated or 0)
    paid=float(fm_row.allocated or 0)
    previous_balance = fixed - allocated

    # Step 3: Validate fund availability
    if allocated_amount > previous_balance:
        frappe.throw(f"Insufficient fund balance ({previous_balance}) in Fund Manager {doc.fund_manager}")

    # Step 4: Create new Fund Utilization Entry
    ledger_entry = frappe.get_doc({
        "doctype": "Fund Utilization Entry",
        "fund_id": doc.fund_manager,
        "organisation": doc.organisation,
        "posting_date": getattr(doc, "date", nowdate()),
        "posting_datetime": now_datetime(),
        "transaction_type": "Utilization",
        "voucher_type": doc.doctype,
        "voucher_no": doc.name,
        "debit": 0,
        "credit": allocated_amount,
        "balance": previous_balance - allocated_amount,
        "remarks": f"Fund utilized from {doc.fund_manager} for {doc.doctype} {doc.name}"
    })
    ledger_entry.insert(ignore_permissions=True)

    # Step 5: Update allocated in Fund Manager Details
    fm_row.allocated = float(fm_row.allocated or 0) + allocated_amount
    fund_doc.save(ignore_permissions=True)

    frappe.logger().info(
        f"Created Fund Utilization Entry for {doc.doctype} {doc.name}, amount {allocated_amount}"
    )

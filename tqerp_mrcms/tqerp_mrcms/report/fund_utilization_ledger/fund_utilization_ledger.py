import frappe
from frappe.utils import flt


def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)

    return columns, data


# ------------------------------------------------------------
# Columns
# ------------------------------------------------------------

def get_columns():
    return [
        {
            "label": "Fund",
            "fieldname": "fund_manager",
            "fieldtype": "Link",
            "options": "Fund Manager",
            "width": 180,
        },
        {
            "label": "Organisation",
            "fieldname": "organisation",
            "fieldtype": "Link",
            "options": "Organisation",
            "width": 200,
        },
        {
            "label": "Posting Date",
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 110,
        },
        {
            "label": "Transaction Type",
            "fieldname": "transaction_type",
            "fieldtype": "Data",
            "width": 140,
        },
        {
            "label": "Voucher Type",
            "fieldname": "voucher_type",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": "Voucher No",
            "fieldname": "voucher_no",
            "fieldtype": "Dynamic Link",
            "options": "voucher_type",
            "width": 180,
        },
        {
            "label": "Debit",
            "fieldname": "debit",
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "label": "Credit",
            "fieldname": "credit",
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "label": "Balance",
            "fieldname": "balance",
            "fieldtype": "Currency",
            "width": 130,
        },
        {
            "label": "Cancelled",
            "fieldname": "is_cancelled",
            "fieldtype": "Check",
            "width": 80,
        },
    ]


# ------------------------------------------------------------
# Data
# ------------------------------------------------------------

def get_data(filters):

    data = []
    running_balance = 0
    total_debit = 0
    total_credit = 0

    # ---------------------------
    # Build Filters
    # ---------------------------

    filter_list = []

    if filters.get("fund_manager"):
        filter_list.append(["fund_id", "=", filters.get("fund_manager")])

    if filters.get("organisation"):
        filter_list.append(["organisation", "=", filters.get("organisation")])

    if filters.get("voucher_type"):
        filter_list.append(["voucher_type", "=", filters.get("voucher_type")])

    if filters.get("voucher_no"):
        filter_list.append(["voucher_no", "=", filters.get("voucher_no")])

    if filters.get("from_date"):
        filter_list.append(["posting_date", ">=", filters.get("from_date")])

    if filters.get("to_date"):
        filter_list.append(["posting_date", "<=", filters.get("to_date")])

    if not filters.get("is_cancelled"):
        # Default → hide cancelled
        filter_list.append(["is_cancelled", "=", 0])

        

    # ---------------------------
    # Fetch Entries
    # ---------------------------

    entries = frappe.get_all(
        "Fund Utilization Entry",
        fields=[
            "fund_id",
            "organisation",
            "posting_date",
            "posting_datetime",
            "transaction_type",
            "voucher_type",
            "voucher_no",
            "debit",
            "credit",
            "is_cancelled",
        ],
        filters=filter_list,
        order_by="posting_date asc, posting_datetime asc",
    )

    # ---------------------------
    # Running Balance Calculation
    # ---------------------------

    for row in entries:

        debit = flt(row.get("debit"))
        credit = flt(row.get("credit"))
        is_cancelled = row.get("is_cancelled")

        if not is_cancelled:
            running_balance += debit - credit
            total_debit += debit
            total_credit += credit

        data.append(
            {
                "fund_manager": row.get("fund_id"),
                "organisation": row.get("organisation"),
                "posting_date": row.get("posting_date"),
                "transaction_type": row.get("transaction_type"),
                "voucher_type": row.get("voucher_type"),
                "voucher_no": row.get("voucher_no"),
                "debit": debit,
                "credit": credit,
                "balance": running_balance,
                "is_cancelled": is_cancelled,
            }
        )

    # ---------------------------
    # Add TOTAL Row
    # ---------------------------

    if data:
        data.append(
            {
                "fund_manager": "TOTAL",
                "organisation": "",
                "posting_date": "",
                "transaction_type": "",
                "voucher_type": "",
                "voucher_no": "",
                "debit": total_debit,
                "credit": total_credit,
                "balance": running_balance,
                "is_cancelled": 0,
            }
        )

    return data

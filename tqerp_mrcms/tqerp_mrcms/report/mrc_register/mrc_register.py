import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 120},
        {"label": _("IP Number"), "fieldname": "ip_no", "fieldtype": "Data", "width": 150},
        {"label": _("IP Name"), "fieldname": "ip_name", "fieldtype": "Data", "width": 180},
        {"label": _("Patient Name"), "fieldname": "name_of_patient", "fieldtype": "Data", "width": 150},
        {"label": _("Dispensary"), "fieldname": "dispensary", "fieldtype": "Data", "width": 150},
        {"label": _("Claim Status"), "fieldname": "claim_status", "fieldtype": "Data", "width": 150},
        {"label": _("Amount Claimed"), "fieldname": "amount_claimed", "fieldtype": "Currency", "width": 150},
        {"label": _("Passed Amount"), "fieldname": "passed_amount", "fieldtype": "Currency", "width": 150},
    ]

def get_data(filters):
    # Basic Condition
    conditions = {"docstatus": 1}

    # Apply Filter
    if filters.get("ip_no"):
        conditions["ip_no"] = filters.get("ip_no")

    if filters.get("claim_status"):
        conditions["claim_status"] = filters.get("claim_status")

    if filters.get("dispensary"):
        conditions["dispensary"] = filters.get("dispensary")

#    Apply Date Filters
    if filters.get("from_date") and filters.get("to_date"):
        conditions["claim_date"] = ["between", (filters.get("from_date"), filters.get("to_date"))]
    elif filters.get("from_date"):
        conditions["claim_date"] = [">=", filters.get("from_date")]
    elif filters.get("to_date"):
        conditions["claim_date"] = ["<=", filters.get("to_date")]

#    Fetch From doctype
    data = frappe.get_all(
        "Claim",
        filters=conditions,
        fields=[
            "claim_date as date",
            "ip_no",
            "ip_name",
            "name_of_patient",
             "dispensary",
            "claim_status",
            "amount_claimed",
            "passed_amount",
        ],
        order_by="claim_date desc"
    )

    return data

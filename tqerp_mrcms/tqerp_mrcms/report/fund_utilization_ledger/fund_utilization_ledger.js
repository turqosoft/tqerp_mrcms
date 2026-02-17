
frappe.query_reports["Fund Utilization Ledger"] = {
    "filters": [
        {
            "fieldname": "fund_manager",
            "label": "Fund Manager",
            "fieldtype": "Link",
            "options": "Fund Manager"
        },
        {
            "fieldname": "organisation",
            "label": "Organisation",
            "fieldtype": "Link",
            "options": "Organisation"
        },
        {
            "fieldname": "from_date",
            "label": "From Date",
            "fieldtype": "Date"
        },
        {
            "fieldname": "to_date",
            "label": "To Date",
            "fieldtype": "Date"
        },
        {
            "fieldname": "voucher_type",
            "label": "Voucher Type",
            "fieldtype": "Select",
            "options": "\nClaim Proceedings\nClaim Payment List\nFund Manager" 
        },
        {
            "fieldname": "voucher_no",
            "label": "Voucher No",
            "fieldtype": "Data"
        },
        {
            fieldname: "is_cancelled",
            label: "Show Cancelled Entries",
            fieldtype: "Check",
            default: 0
        }
        
    ]
};

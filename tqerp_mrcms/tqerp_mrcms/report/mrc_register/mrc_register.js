frappe.query_reports["Mrc Register"] = {
    "filters": [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 0
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 0
        },
        {
            fieldname: "ip_no",
            label: __("IP Number"),
            fieldtype: "Data",
            reqd: 0
        },
        {
            fieldname: "dispensary",
            label: __("Dispensary"),
            fieldtype: "Data",
            reqd: 0
        },
        {
            fieldname: "claim_status",
            label: __("Claim Status"),
            fieldtype: "Select",
            options: [
                "",
                "Draft",
                "HC Review",
                "IMO Review",
                "RD Review",
                "Join Director Review",
                "Director Review",
                "Sanctioned",
                "Paid",
                "Objection"
            ].join("\n"),
            reqd: 0
        }
    ]
};

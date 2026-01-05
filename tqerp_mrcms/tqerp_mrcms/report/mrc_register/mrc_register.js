frappe.query_reports["MRC Register"] = {
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
            fieldtype: "Link",
            options: "Organisation",
            reqd: 0
        },
        {
            fieldname: "workflow_state",
            label: __("Workflow"),
            fieldtype: "Select",
            options: [
                "",
                "Draft",
                "HC Review",
                "IMO Review",
                "Sanctioned",
                "RDD Section",
                "RDD Review",
                "JS/SS Review",
                "JD Section",
                "JD Review",
                "Director Review",
                "Govt Review",
                "Rejected",
                "Returned",
            ].join("\n"),
            reqd: 0
        },
        {
            fieldname: "claim_status",
            label: __("Claim Status"),
            fieldtype: "Select",
            options: [
                "",
                "Data Entry",
                "Registered",
                "Processing",
                "Sanctioned",
                "Rejected",
                "Returned",
                "Paid",
                "Closed"
            ].join("\n"),
            reqd: 0
        }
    ]
};

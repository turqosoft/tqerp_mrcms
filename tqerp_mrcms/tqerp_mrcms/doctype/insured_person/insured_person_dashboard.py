from frappe import _

def get_data():
    return {
        "fieldname": "ip_no",  # Link field name in Claim doctype
        "transactions": [
            {
                "label": _("Claim"),
                "items": ["Claim"]
            }
        ]
    }

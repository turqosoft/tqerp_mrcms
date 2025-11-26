from frappe import _

def get_data():
    return {
        "fieldname": "bank",  # this should match the Link field in Account Details
        "transactions": [
            {
                "label": _("Account Details"),
                "items": ["Account Details"]
            }
        ]
    }

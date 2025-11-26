from frappe import _

def get_data():
    return {
        "fieldname": "claim_type",  # Link field name in Claim doctype
        "transactions": [
            {
                "label": _("Claim Processing"),
                "items": ["Claim Processing"]
            }
        ]
    }

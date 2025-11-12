from frappe import _

def get_data():
    return {
        "fieldname": "insured_person",  # Link field name in Claim doctype
        "transactions": [
            {
                "label": _("Claim"),
                "items": ["Claim"]
            }
        ]
    }

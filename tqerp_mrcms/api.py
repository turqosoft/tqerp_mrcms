import frappe

# tqerp_mrcms/api.py

import json
from frappe.utils import cint
from frappe import _

# @frappe.whitelist(allow_guest=False)
# def submit_claim(data):
#     claim_data = json.loads(data)
#     claim = frappe.get_doc({
#         "doctype": "Claim",
#         "ip_no": claim_data.get("ip_no"),
#         "ip_name": claim_data.get("ip_name"),
#         "receipt_no": claim_data.get("receipt_no"),
#         "receipt_date": claim_data.get("receipt_date"),
#         "amount_claimed": claim_data.get("amount_claimed"),
#         "claim_type": claim_data.get("claim_type"),
#         "category": claim_data.get("category"),
#         "claim_begin_date": claim_data.get("claim_begin_date"),
#         "claim_end_date": claim_data.get("claim_end_date"),
#         "diseases": claim_data.get("diseases"),
#         "hospital": claim_data.get("hospital"),
#         "rule": claim_data.get("rule"),
#         "nominee": claim_data.get("nominee"),
#         "name_of_patient": claim_data.get("name_of_patient"),
#         "relation": claim_data.get("relation"),
#         "age_of_patient": claim_data.get("age_of_patient"),
#         "claim_templates": claim_data.get("claim_templates"),
#         "claim_checklist": claim_data.get("claim_checklist")
#     })
#     claim.insert()
#     frappe.db.commit()
#     return {"status": "success", "claim_id": claim.name}


@frappe.whitelist()
def create_claim(ip_name=None, **kwargs):
    if not ip_name:
        frappe.throw("IP No is required.")

    # Create Claim document
    doc = frappe.new_doc("Claim")
    
    # Basic fields
    doc.ip_no = ip_name
    doc.ip_name = kwargs.get("ip_name")
    doc.receipt_no = kwargs.get("receipt_no")
    doc.receipt_date = kwargs.get("receipt_date")
    doc.amount_claimed = kwargs.get("amount_claimed")
    doc.claim_type = kwargs.get("claim_type")
    doc.category = kwargs.get("category")
    doc.claim_begin_date = kwargs.get("claim_begin_date")
    doc.claim_end_date = kwargs.get("claim_end_date")
    doc.diseases = kwargs.get("diseases")
    doc.hospital = kwargs.get("hospital")
    doc.rule = kwargs.get("rule")
    doc.nominee = kwargs.get("nominee")

    # Patient Details
    doc.name_of_patient = kwargs.get("name_of_patient")
    doc.relation = kwargs.get("relation")
    doc.age_of_patient = kwargs.get("age_of_patient")

    # Checklist
    doc.claim_templates = kwargs.get("claim_templates")
    doc.claim_checklist = kwargs.get("claim_checklist")

    doc.save(ignore_permissions=True)

    return {"status": "success", "claim_id": doc.name}


@frappe.whitelist()
def get_ip_for_claim(doctype, txt=None, searchfield=None, start=0, page_length=10, filters=None, **kwargs):
    """
    Used for ip_no link field in Claim.
    Returns [[ip_no, ip_name], ...] to show in dropdown.
    """
    filters = filters or {}

    # Get matching insured persons
    ip_list = frappe.get_all(
        "Insured Person",
        filters={"ip_no": ["like", f"%{txt}%"]},  # Search by ip_no
        fields=["name", "ip_name"],
        limit_start=start,
        limit_page_length=page_length
    )

    # Log for debugging
    frappe.log_error(message=str(ip_list), title="IP List Debug")

    # Convert to list of lists for link field dropdown
    return [[ip.name, ip.ip_name] for ip in ip_list]


@frappe.whitelist()
def get_family_members_for_claim(filters=None):
    """
    Returns family members of an Insured Person.
    filters should be JSON string: {"ip_no": "IP-0001"}
    Returns list of dicts:
    { "member_name": "...", "relation": "...", "age": ..., "nominee": "...", "hospital": "...", "rule": "..." }
    """
    if filters:
        try:
            filters = json.loads(filters)
        except Exception:
            filters = {}
    else:
        filters = {}

    ip_no = filters.get("ip_no")
    if not ip_no:
        return []

    try:
        family_doc = frappe.get_doc("Insured Person", ip_no)
    except frappe.DoesNotExistError:
        return []

    result = []

    for row in getattr(family_doc, "family_members", []):
        result.append({
            "member_name": row.member_name,
            "relation": row.relation,
            "age": getattr(row, "age_of_member", ""),
            "nominee": getattr(row, "nominee", ""),
            "hospital": getattr(row, "hospital", ""),
            "rule": getattr(row, "rule", "")
        })

    return result

import frappe

@frappe.whitelist()
def get_ip_details(ip_no):

    if not ip_no:
        return {}

    ip = frappe.get_doc("Insured Person", ip_no)

    return {
        "ip_name": ip.ip_name,
        "ip_address": ip.address,
        "employer": ip.employer,
        "phone": ip.phone,
        "dob": ip.dob,
        "gender": ip.gender,
        "dispensary": ip.dispensary,
        "family_members": ip.family_members,
        "bank_accounts": ip.bank_accounts,
        "entitlement": ip.entitlement,
        "nominee_details": ip.nominee_details
    }

@frappe.whitelist()
def get_autocomplete_list(doctype):
    """Return name list for autocomplete (no /api/resource call)."""
    try:
        records = frappe.get_all(doctype, pluck="name")
        return {"status": "success", "data": records}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def create_insured_person():
    import json, frappe
    try:
        data = json.loads(frappe.local.request.get_data().decode("utf-8"))
        
        ip = frappe.new_doc("Insured Person")
        ip.insurance_no = data.get("insurance_no")
        ip.ip_no = data.get("ip_no")
        ip.ip_name = data.get("ip_name")
        ip.address = data.get("address")
        ip.gender = data.get("gender")
        ip.dob = data.get("dob")
        ip.phone = data.get("phone")
        ip.local_office = data.get("local_office")
        ip.employer = data.get("employer")
        ip.nominee = data.get("nominee")

        for row in data.get("family", []):
            ip.append("family_members", row)
        for row in data.get("bank_accounts", []):
            ip.append("bank_accounts", row)
        for row in data.get("entitlement", []):
            ip.append("entitlement", row)

        ip.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"status": "success", "ip_no": ip.name}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Create IP Error")
        return {"status": "error", "message": str(e)}



@frappe.whitelist()
def create_claim_from_ip(ip_no):

    # Load Insured Person
    ip = frappe.get_doc("Insured Person", ip_no)

    # Create new Claim
    claim = frappe.new_doc("Claim")

    # Basic field mapping
    claim.ip_no = ip.ip_no
    claim.ip_name = ip.ip_name
    claim.mobile_ph = ip.phone
    claim.address = ip.address
    claim.workplace = ip.employer

    # ---------------- NOMINEE (CHILD TABLE → SINGLE FIELD) ----------------
    # Child table name: nominee_details
    # Fields: name_of_nominee, relation_with_ip, date_of_birth, uhidabha_number, address, percentage

    if ip.nominee_details:
        # Picking the *first* nominee — you can change logic if needed
        row = ip.nominee_details[0]

        # Map only name_of_nominee to Claim.nominee
        claim.nominee = row.name_of_nominee

        # If you want to store more nominee data in claim, add more fields:
        claim.nominee_relation = row.relation_with_ip
        claim.nominee_dob = row.date_of_birth
        claim.nominee_uhid = row.uhidabha_number
        claim.nominee_address = row.address
        claim.nominee_percentage = row.percentage

    # ---------------- BANK DETAILS ----------------
    bank_row = None

    if ip.bank_accounts:
        # Prefer default account
        for row in ip.bank_accounts:
            if row.default_account:
                bank_row = row
                break

        # If no default, use first
        if not bank_row:
            bank_row = ip.bank_accounts[0]

        # Copy to Claim
        claim.bank_name = bank_row.bank
        claim.branch = bank_row.branch
        claim.ifs_code = bank_row.ifsc_code
        claim.bank_account_no = bank_row.acc_no

    # Save Claim
    claim.insert(ignore_permissions=True)
    return claim.name

@frappe.whitelist()
def get_next_claim_series():
    # This will get the next number according to the series defined in Naming Series master
    series_name = "CLM-.YYYY.-.#####"
    return frappe.model.naming.make_autoname(series_name)


@frappe.whitelist(allow_guest=False)
def check_page_permission(doc, ptype="read"):
    if "Cleark" in frappe.get_roles():
        return True
    return False

@frappe.whitelist()
def get_dashboard_stats():
    stats = {
        "total_claims": frappe.db.count("Claim"),
        "total_approved": frappe.db.count("Claim", {"claim_status": "Approved"}),
        "total_initiated": frappe.db.count("Claim", {"claim_status": "Initiated"}),
        "total_insured": frappe.db.count("Insured Person")
    }
    return stats

@frappe.whitelist()
def search_insured_persons(filters):
    """Search Insured Person records with pagination and filters.

    Expected filters (JSON string from frontend):
    {
        "page": 1,
        "page_size": 10,
        "ip_no": "123",
        "ip_name": "john",
        "phone": "9876"
    }
    """
    # Parse filters JSON from string to dict
    try:
        f = json.loads(filters)
    except Exception:
        f = {}

    page = int(f.get("page", 1)) or 1
    page_size = int(f.get("page_size", 10)) or 10
    offset = (page - 1) * page_size

    # Build conditions & args safely
    conditions = "1=1"
    args = {}

    if f.get("ip_no"):
        conditions += " AND ip_no LIKE %(ip_no)s"
        args["ip_no"] = f"%{f['ip_no']}%"

    if f.get("ip_name"):
        conditions += " AND ip_name LIKE %(ip_name)s"
        args["ip_name"] = f"%{f['ip_name']}%"

    if f.get("phone"):
        conditions += " AND phone LIKE %(phone)s"
        args["phone"] = f"%{f['phone']}%"

    # Count total (for pagination)
    # Note: frappe.db.count with filters=dict won't accept raw SQL conditions,
    # so we reuse the same WHERE manually.
    total_count = frappe.db.sql(
        f"""
        SELECT COUNT(*)
        FROM `tabInsured Person`
        WHERE {conditions}
        """,
        args,
    )[0][0]

    total_pages = (total_count // page_size) + (1 if total_count % page_size else 0)

    # Fetch paginated records
    data = frappe.db.sql(
        f"""
        SELECT
            name,
            ip_no,
            ip_name,
            phone,
            employer
        FROM `tabInsured Person`
        WHERE {conditions}
        ORDER BY ip_name
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        {**args, "limit": page_size, "offset": offset},
        as_dict=True,
    )

    return {
        "list": data,
        "total_pages": total_pages,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
    }

@frappe.whitelist()
def search_claims(filters):
    """Search Claim records with pagination and filters.

    Expected filters (JSON string from frontend):
    {
        "page": 1,
        "page_size": 10,
        "from_date": "2025-01-01",
        "to_date": "2025-01-31",
        "insurance_no": "123",
        "status": "Draft"
    }
    """
    try:
        f = json.loads(filters)
    except Exception:
        f = {}

    page = int(f.get("page", 1)) or 1
    page_size = int(f.get("page_size", 10)) or 10
    offset = (page - 1) * page_size

    conditions = "1=1"
    args = {}

    # Date range filter (form_date)
    if f.get("from_date"):
        conditions += " AND claim_date >= %(from_date)s"
        args["from_date"] = f["from_date"]

    if f.get("to_date"):
        conditions += " AND claim_date <= %(to_date)s"
        args["to_date"] = f["to_date"]

    # Insurance No filter
    if f.get("insurance_no"):
        conditions += " AND ip_no LIKE %(insurance_no)s"
        args["insurance_no"] = f"%{f['insurance_no']}%"

    # Status filter
    if f.get("status"):
        conditions += " AND claim_status = %(status)s"
        args["status"] = f["status"]

    # Total count for pagination
    total_count = frappe.db.sql(
        f"""
        SELECT COUNT(*)
        FROM `tabClaim`
        WHERE {conditions}
        """,
        args,
    )[0][0]

    total_pages = (total_count // page_size) + (1 if total_count % page_size else 0)

    # Fetch page of claims
    data = frappe.db.sql(
        f"""
        SELECT
            name,
            ip_no,
            ip_name,
            name_of_patient,
            age_of_patient,
            relation,
            amount_claimed,
            claim_status,
            claim_date
        FROM `tabClaim`
        WHERE {conditions}
        ORDER BY claim_date DESC, creation DESC
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        {**args, "limit": page_size, "offset": offset},
        as_dict=True,
    )

    return {
        "list": data,
        "total_pages": total_pages,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
    }
@frappe.whitelist()
def save_claim():
    import json
    data = frappe.local.form_dict  # or json.loads(frappe.local.request.get_data())

    claim_name = data.get("claim_name")

    if claim_name:
        doc = frappe.get_doc("Claim", claim_name)  # EDIT existing
    else:
        doc = frappe.new_doc("Claim")  # CREATE new

    # -------------------------
    # Update main/master fields
    # -------------------------
    main_fields = [
        "ip_no", "phone", "address", "ip_name", "book_no", "employer",
        "name_of_patient", "age_of_patient", "relation", "from_date", "to_date",
        "type", "hospital", "in_patient_no", "diseases", "amount_claimed",
        "bank_name", "branch", "bank_account_no", "ifs_code", "claim_status",
        "claim_date", "form_no", "passed_amount", "passed_amount_words",
        "voucher_no", "remarks"
    ]
    for field in main_fields:
        if field in data:
            doc.set(field, data[field])

    # -------------------------
    # Update child tables
    # -------------------------
    if "bill_details" in data:
        doc.set("bill_details", data["bill_details"])
    if "contacted_ip" in data:
        doc.set("contacted_ip", data["contacted_ip"])

    # -------------------------
    # Save the document
    # -------------------------
    doc.save()
    frappe.db.commit()  # commit changes
    return {"claim_name": doc.name}




@frappe.whitelist()
def get_ip_details(ip_no: str):
    """Fetch Insured Person + family details for pre-filling the claim form."""
    if not ip_no:
        return None

    # Adjust the DocType and fieldnames as per your actual schema
    ip_doc = frappe.get_doc("Insured Person", {"ip_no": ip_no})

    return frappe._dict(
        ip_no=ip_doc.ip_no,
        phone=ip_doc.phone,
        ip_name=ip_doc.ip_name,
        address=getattr(ip_doc, "address", ""),
        employer=getattr(ip_doc, "employer", ""),
        bank_name=getattr(ip_doc, "bank_name", ""),
        branch=getattr(ip_doc, "branch", ""),
        bank_ac_no=getattr(ip_doc, "bank_ac_no", ""),
        ifsc=getattr(ip_doc, "ifsc", ""),
        dispensary=getattr(ip_doc, "dispensary", ""),
        family_members=ip_doc.get("family_members") or []
    )


@frappe.whitelist()
def get_ip_details(ip_no: str):
    """Fetch Insured Person + family details for pre-filling the claim form."""
    if not ip_no:
        return None

    # Adjust the DocType and fieldnames as per your actual schema
    ip_doc = frappe.get_doc("Insured Person", {"ip_no": ip_no})

    return frappe._dict(
        ip_no=ip_doc.ip_no,
        phone=ip_doc.phone,
        ip_name=ip_doc.ip_name,
        address=getattr(ip_doc, "address", ""),
        employer=getattr(ip_doc, "employer", ""),
        bank_name=getattr(ip_doc, "bank_name", ""),
        branch=getattr(ip_doc, "branch", ""),
        bank_ac_no=getattr(ip_doc, "bank_ac_no", ""),
        ifsc=getattr(ip_doc, "ifsc", ""),
        dispensary=getattr(ip_doc, "dispensary", ""),
        family_members=ip_doc.get("family_members") or []
    )


@frappe.whitelist()
def get_claim_by_form_no():
    claim_no = frappe.form_dict.get("claim_no")  # this is the doc.name
    if not claim_no:
        return {"error": "claim_no missing"}

    try:
        doc = frappe.get_doc("Claim", claim_no)

        return {
            "claim": doc.as_dict(),
            "bill_details": [row.as_dict() for row in doc.get("bill_details") or []],
            "contacted_ip": [row.as_dict() for row in doc.get("ip_communication") or []]
        }

    except Exception:
        frappe.log_error(frappe.get_traceback(), "get_claim_by_form_no")
        return {"error": "Error fetching claim details, check logs"}



import frappe, json

@frappe.whitelist(allow_guest=False)
def update_claim():
    """
    Update an existing Claim document from JSON payload.
    Expects child tables as arrays of dicts:
    - bill_details: [{"bill_date":..., "bill_no":..., "bill_amount":...}]
    - contacted_ip: [{"contacted_ip_date":..., "contacted_ip_by":..., "contacted_ip_remarks":...}]
    """
    try:
        # -------------------------
        # Get payload
        # -------------------------
        data = frappe.request.get_json() or frappe.local.form_dict or {}
        frappe.log_error(json.dumps(data, default=str), "Update Claim Payload")

        # Use form_no or name as document identifier
        doc_name = data.get("name") or data.get("form_no")
        if not doc_name:
            return {"error": "Document identifier (form_no) is required for update"}

        # -------------------------
        # Fetch existing claim
        # -------------------------
        if not frappe.db.exists("Claim", doc_name):
            return {"error": f"Claim '{doc_name}' does not exist"}

        doc = frappe.get_doc("Claim", doc_name)

        # -------------------------
        # Correct mapping (HTML -> DocType)
        # -------------------------
        field_map = {
            "insurance_no": "ip_no",
            "mobile": "phone",
            "ip_address": "address",
            "ip_name": "ip_name",
            "esi_book_no": "book_no",
            "employer_name": "employer",
            "patient_name": "name_of_patient",   # ✅ Make sure fieldname matches DocType
            "patient_age": "age_of_patient",
            # "relationship": "relation",
            "treat_from": "from_date",
            "treat_to": "to_date",
            "treatment_type": "type",
            "ip_treatment_details": "hospital",
            "in_patient_no": "in_patient_no",
            "diagnosis": "diseases",
            "claim_amount": "amount_claimed",
            "bank_name": "bank_name",
            "branch": "branch",
            "bank_ac_no": "bank_account_no",
            "ifsc": "ifs_code",
            "claim_status": "claim_status",
            "claim_date": "claim_date",
            "form_no": "name",
            "passed_amount": "passed_amount",
            "passed_amount_words": "passed_amount_words",
            "voucher_no": "voucher_no",
            "remarks": "remarks"
        }

        # -------------------------
        # Update main fields safely
        # -------------------------
        for html_field, dt_field in field_map.items():
            if html_field in data:
                val = data.get(html_field)
                if isinstance(val, str):
                    val = val[:140]  # truncate long strings
                if hasattr(doc, dt_field):
                    doc.set(dt_field, val or "")
                    frappe.log_error(f"Setting {dt_field} = {val}", "Update Claim Debug")

        # -------------------------
        # Update Bill Details child table
        # -------------------------
        if isinstance(data.get("bill_details"), list):
            doc.set("bill_details", [])
            for row in data["bill_details"]:
                doc.append("bill_details", {
                    "bill_date": row.get("bill_date") or None,
                    "bill_no": str(row.get("bill_no") or "")[:140],
                    "bill_amount": float(str(row.get("bill_amount") or 0).replace(",", ""))
                })

        # -------------------------
        # Update Contacted IP child table
        # -------------------------
        if isinstance(data.get("contacted_ip"), list):
            doc.set("ip_communication", [])
            for row in data["contacted_ip"]:
                if not any([row.get("contacted_ip_date"), row.get("contacted_ip_by"), row.get("contacted_ip_remarks")]):
                    continue
                doc.append("ip_communication", {
                    "date": row.get("contacted_ip_date") or None,
                    "name1": (row.get("contacted_ip_by") or "")[:140],
                    "remarks": (row.get("contacted_ip_remarks") or "")[:140]
                })

        # -------------------------
        # Save and commit
        # -------------------------
        doc.save(ignore_permissions=True)
        frappe.db.commit()

        return {"name": doc.name}

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Update Claim Failed")
        return {"error": "Failed to update claim. Check server logs."}

@frappe.whitelist()
def get_ip_details_list(doctype, txt, searchfield, start, page_len, filters):
    return frappe.db.sql("""
        SELECT
            ip_no,
            CONCAT(ip_no, ' - ', MAX(ip_name), ' - ', MAX(phone))
        FROM `tabInsured Person`
        WHERE
            ip_no LIKE %(txt)s
            OR ip_name LIKE %(txt)s
            OR phone LIKE %(txt)s
        GROUP BY ip_no
        ORDER BY MAX(ip_name) ASC
        LIMIT %(start)s, %(page_len)s
    """, {
        "txt": f"%{txt}%",
        "start": start,
        "page_len": page_len
    })




import frappe
from datetime import datetime, date

@frappe.whitelist()
def get_family_members_for_dropdown(ip_no):
    """Return list of family member names for a given Insured Person"""
    if not ip_no:
        return []

    try:
        ip_doc = frappe.get_doc("Insured Person", ip_no)
        return [f.member_name for f in getattr(ip_doc, "family_members", [])]
    except frappe.DoesNotExistError:
        return []

@frappe.whitelist()
def get_family_member_details(ip_no, member_name):
    """Return relation and age_of_patient for selected family member"""
    if not ip_no or not member_name:
        return {}

    try:
        ip_doc = frappe.get_doc("Insured Person", ip_no)
        for f in getattr(ip_doc, "family_members", []):
            if f.member_name == member_name:
                # Calculate age from dob
                age = None
                if f.dob:
                    dob = f.dob
                    if isinstance(dob, str):
                        dob = datetime.strptime(dob, "%Y-%m-%d").date()
                    today = date.today()
                    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

                return {
                    "relation": f.relation or "",
                    "age_of_patient": age
                }
        return {}
    except frappe.DoesNotExistError:
        return {}




import frappe
import json

@frappe.whitelist()
def create_claim_proceeding_for_multiple(claims_data):
    """
    Create ONE Claim Proceedings document with all selected claims in the child table
    """
    if not claims_data:
        frappe.throw("No claims selected.")

    # Parse JSON string if needed
    if isinstance(claims_data, str):
        claims_data = json.loads(claims_data)

    # Create parent document
    cp = frappe.get_doc({
        "doctype": "Claim Proceedings",
        "naming_series": "CP-.YYYY.-",  # <-- set on parent
        "claim_proceedings": []         # child table fieldname
    })

    # Append each selected claim to the child table
    for claim in claims_data:
        cp.append("claim_proceedings", {  # must be child table fieldname
        "claim_no": claim.get("claim_no", ""),
            "name1": claim.get("ip_name", ""),
            "ip_no": claim.get("ip_no", ""),
            "claim_date": claim.get("claim_date", ""),
            "phone": claim.get("phone", ""),
            "ifsc": claim.get("ifs_code", ""),
            "bank_account_no": claim.get("bank_account_no", ""),
            "passed_amount": claim.get("passed_amount", 0)
        })

    cp.insert(ignore_permissions=True)
    return {"name": cp.name}
# your_app/api.py

import frappe

@frappe.whitelist()
def get_claim_dates_for_print(claim_name):
    """
    Returns earliest and latest claim_date for all claim_no in claim_proceedings child table
    """
    doc = frappe.get_doc("Claim", claim_name)
    dates = []

    for row in doc.claim_proceedings:
        if row.claim_no:
            try:
                claim_doc = frappe.get_doc("Claim", row.claim_no)
                if claim_doc.claim_date:
                    dates.append(claim_doc.claim_date)
            except frappe.DoesNotExistError:
                continue

    if dates:
        earliest = min(dates)
        latest = max(dates)
        return {"earliest": earliest, "latest": latest}
    else:
        return {"earliest": None, "latest": None}

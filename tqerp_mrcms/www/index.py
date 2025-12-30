import frappe
import json
from frappe.utils import now_datetime
from tqerp_mrcms.api import get_claim_dashboard_data

def get_context(context):
    context.allow_guest = True
    context.intro_text = "Medical Reimbursement Claim Management System"
    context.now = now_datetime()

    # Fetch real stats from the API
    try:
        dashboard_data = get_claim_dashboard_data()
        context.stats = dashboard_data.get("summary", {})
        context.financial = dashboard_data.get("financial", {})
        context.dashboard_data_json = json.dumps(dashboard_data)
        
        # Transform chart data back to dict for template iteration
        raw_status = dashboard_data.get("status_overview", {})
        if raw_status:
            context.status_counts = dict(zip(raw_status.get("labels", []), raw_status.get("values", [])))
        else:
            context.status_counts = {}
    except Exception as e:
        frappe.log_error(f"Failed to load dashboard data: {e}", "MRCMS Portal")
        context.stats = {
            "total_claims": 0,
            "approved": 0,
            "paid": 0,
            "pending": 0
        }

    # Fetch user manuals (if any)
    # Assumes "File" doctype has attachments for "Mrcms Settings" or similar
    # For now, we search for files attached to 'Mrcms Settings' or labeled 'Public'
    context.manuals = frappe.get_all(
        "File",
        filters={
            "is_private": 0,
            "attached_to_name": ["like", "%Manual%"] 
        },
        fields=["file_name as title", "file_url"],
        limit=5
    )

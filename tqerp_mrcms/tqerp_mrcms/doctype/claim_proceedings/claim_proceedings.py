# Copyright (c) 2025, turqosoft and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

class ClaimProceedings(Document):
    
    def after_insert(self):
        """Log creation of a new Claim"""
        # Optional: You may still log creation if needed
        pass
    
    def on_cancel(self):
 
        # ------------------------------------------
        # 1️ Reverse Fund (if allocated)
        # ------------------------------------------
        if self.fund_manager and self.total_allocated:
            frappe.get_attr("tqerp_mrcms.api.reverse_fund_on_cancel")(
                self.name,
                doctype="Claim Proceedings"
            )
 
        # ------------------------------------------
        # 2️ Mark Fund Utilization Entry as Cancelled
        # ------------------------------------------
        entries = frappe.get_all(
            "Fund Utilization Entry",
            filters={
                "voucher_no": self.name,
                "transaction_type": "Utilization",
                "is_cancelled": 0
            }
        )
 
        for entry in entries:
            frappe.db.set_value(
                "Fund Utilization Entry",
                entry.name,
                "is_cancelled",
                1
            )
 
        # ------------------------------------------
        # 3 Clear link + Reset claim status
        # ------------------------------------------
        for row in self.claim_proceedings:
            if row.claim_no:
 
                claim_doc = frappe.get_doc("Claim", row.claim_no)
 
                # Clear Claim Proceedings link
                claim_doc.claim_proceedings = None
 
                # Reset claim status
                claim_doc.claim_status = "Sanctioned"
 
                claim_doc.save(ignore_permissions=True)
 

    # def validate(self):
    #     """
    #     Prevent creating Claim Proceedings if the claim
    #     already has:
    #     1) a Claim Bundle
    #     2) another Claim Proceedings
    #     """
    #     for row in self.claim_proceedings:
    #         if not row.claim_no:
    #             continue
 
    #         # 1️⃣ Check Claim Bundle
    #         bundle = frappe.db.get_value(
    #             "Claim",
    #             row.claim_no,
    #             "claim_bundle_management"
    #         )
 
    #         if bundle:
    #             frappe.throw(
    #                 f"❌ Claim {row.claim_no} is already linked to "
    #                 f"Claim Bundle <b>{bundle}</b>. "
    #                 f"You cannot create Claim Proceedings for this claim."
    #             )
 
    #         # 2️⃣ Check Claim Proceedings
    #         existing_cp = frappe.db.get_value(
    #             "Claim",
    #             row.claim_no,
    #             "claim_proceedings"
    #         )
 
    #         # Allow if editing same document
    #         if existing_cp and existing_cp != self.name:
    #             frappe.throw(
    #                 f"❌ Claim {row.claim_no} is already linked to "
    #                 f"Claim Proceedings <b>{existing_cp}</b>. "
    #                 f"You cannot create another Claim Proceedings for this claim."
    #             )
 
    def validate(self):
        """
        Prevent creating Claim Proceedings if:
        1) Claim category is not allowed
        2) Claim already has a Claim Bundle
        3) Claim already has another Claim Proceedings
        """
 
        allowed_categories = ["Category A", "Category B"]
 
        for row in self.claim_proceedings:
            if not row.claim_no:
                continue
 
            # 🔹 Fetch required fields from Claim
            claim_data = frappe.db.get_value(
                "Claim",
                row.claim_no,
                [
                    "claim_category",
                    "claim_bundle_management",
                    "claim_proceedings"
                ],
                as_dict=True
            )
 
            if not claim_data:
                continue
 
            # Validate Claim Category
            if claim_data.claim_category not in allowed_categories:
                frappe.throw(
                    f"❌ Claim <b>{row.claim_no}</b> belongs to "
                    f"<b>{claim_data.claim_category}</b> category.<br>"
                    f"Only <b>Category A</b> and <b>Category B</b> "
                    f"can create Claim Proceedings."
                )
 
            #  Check Claim Bundle
            if claim_data.claim_bundle_management:
                frappe.throw(
                    f"❌ Claim <b>{row.claim_no}</b> is already linked to "
                    f"Claim Bundle <b>{claim_data.claim_bundle_management}</b>.<br>"
                    f"You cannot create Claim Proceedings for this claim."
                )
 
            #  Check existing Claim Proceedings
            if claim_data.claim_proceedings and claim_data.claim_proceedings != self.name:
                frappe.throw(
                    f"❌ Claim <b>{row.claim_no}</b> is already linked to "
                    f"Claim Proceedings <b>{claim_data.claim_proceedings}</b>.<br>"
                    f"You cannot create another Claim Proceedings for this claim."
                )
 
    # --------------------------------------------------
    # BEFORE SAVE
    # --------------------------------------------------
    def before_save(self):
 
        # ------------------------------------------
        # 1️⃣ Refund old fund if Fund Manager changed
        # ------------------------------------------
        if not self.is_new():
 
            old_fund = frappe.db.get_value(
                self.doctype,
                self.name,
                "fund_manager"
            )
 
            if old_fund and old_fund != self.fund_manager:
                from tqerp_mrcms.api import reverse_fund_on_cancel
 
                reverse_fund_on_cancel(
                    name=self.name,
                    doctype=self.doctype
                )
 
        # ------------------------------------------
        # 2️⃣ Handle Claim Link Updates
        # ------------------------------------------
 
        # 🔹 Get OLD claims from DB
        old_claims = set()
        if not self.is_new():
            old_rows = frappe.get_all(
                "Claim Proceedings Details",  
                filters={"parent": self.name},
                pluck="claim_no"
            )
            old_claims = set(old_rows)
 
        # 🔹 Get CURRENT claims from document
        current_claims = set()
        for row in self.claim_proceedings:
            if row.claim_no:
                current_claims.add(row.claim_no)
 
        # 🔹 Claims removed
        removed_claims = old_claims - current_claims
 
        # 🔹 Claims added
        added_claims = current_claims - old_claims
 
        # ------------------------------------------
        # 3️⃣ Clear removed claims
        # ------------------------------------------
        for claim in removed_claims:
            current_link = frappe.db.get_value(
                "Claim",
                claim,
                "claim_proceedings"
            )
 
            if current_link == self.name:
                frappe.db.set_value(
                    "Claim",
                    claim,
                    "claim_proceedings",
                    None
                )
 
        # ------------------------------------------
        # 4️⃣ Set new/remaining claims
        # ------------------------------------------
        for claim in current_claims:
            frappe.db.set_value(
                "Claim",
                claim,
                "claim_proceedings",
                self.name
            )
 
 
    # --------------------------------------------------
    # ON TRASH
    # --------------------------------------------------
    def on_trash(self):
 
        from tqerp_mrcms.api import reverse_fund_on_cancel
 
        # ------------------------------------------
        # 1️⃣ Reverse allocated fund
        # ------------------------------------------
        reverse_fund_on_cancel(
            name=self.name,
            doctype=self.doctype
        )
 
        # ------------------------------------------
        # 2️⃣ Clear claim_proceedings link safely
        # ------------------------------------------
        for row in self.claim_proceedings:
            if not row.claim_no:
                continue
 
            current_link = frappe.db.get_value(
                "Claim",
                row.claim_no,
                "claim_proceedings"
            )
 
            # Only unlink if THIS CP set it
            if current_link == self.name:
                frappe.db.set_value(
                    "Claim",
                    row.claim_no,
                    "claim_proceedings",
                    None
                )

def get_child_organisations(root_office):
    """Return root_office + all its descendants using parent_organisation."""
    to_visit = [root_office]
    all_offices = set()

    while to_visit:
        current = to_visit.pop()
        if current in all_offices:
            continue

        all_offices.add(current)

        children = frappe.get_all(
            "Organisation",
            filters={"parent_organisation": current},
            pluck="name"
        )
        to_visit.extend(children)

    return list(all_offices)


def get_permission_query_conditions(user):
		if not user:
			user = frappe.session.user

		# Full access for Administrator (and optionally System Manager etc.)
		if user in ("Administrator"):
			return ""

		# If you have a special role that should see everything, uncomment:
		# if "MRCMS Admin" in frappe.get_roles(user):
		#     return ""

		# Get user's organisation 
		user_org = frappe.db.get_value("User", user, "organisation")
		if not user_org:
			# No organisation assigned → see nothing
			return "1=0"

		organisations = get_child_organisations(user_org)
		if not organisations:
			organisations = [user_org]

		escaped_orgs = ", ".join(frappe.db.escape(o) for o in organisations)

		return f"`tabClaim Proceedings`.`organisation` in ({escaped_orgs})"

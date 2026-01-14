// -----------------------------------------------------
// Claim ListView Settings
// -----------------------------------------------------
frappe.listview_settings['Claim'] = {
    order_by: 'claim_date desc',

    onload: async function (listview) {
        console.log("Claim ListView loaded.");
        try {
            // -----------------------------------------------------
            //  Add Action Button — Create Claim Proceedings
            // -----------------------------------------------------
            listview.page.add_action_item(__('Claim Proceedings'), async function () {

                let selected_docs = listview.get_checked_items();
                if (!selected_docs.length) {
                    frappe.msgprint(__('Please select at least one claim.'));
                    return;
                }

                let sanctioned_claims = [];

                for (let doc of selected_docs) {
                    let full_doc = await frappe.db.get_doc('Claim', doc.name);

                    if (full_doc.claim_status === "Sanctioned") {
                        sanctioned_claims.push({
                            claim_no: full_doc.claim_no || full_doc.name,
                            claim_date: full_doc.claim_date || "",
                            ip_name: full_doc.ip_name || "",
                            ip_no: full_doc.ip_no || "",
                            phone: full_doc.phone || "",
                            ifs_code: full_doc.ifs_code || "",
                            bank_account_no: full_doc.bank_account_no || "",
                            passed_amount: full_doc.passed_amount || 0
                        });
                    }
                }

                if (!sanctioned_claims.length) {
                    frappe.msgprint(__('No selected claims are sanctioned.'));
                    return;
                }

                try {
                    let r = await frappe.call({
                        method: "tqerp_mrcms.api.create_claim_proceeding_for_multiple",
                        args: { claims_data: JSON.stringify(sanctioned_claims) }
                    });

                    if (r.message?.name) {
                        frappe.set_route("Form", "Claim Proceedings", r.message.name);
                        frappe.msgprint(__('Claim Proceedings created.'));
                    }

                } catch (err) {
                   
                    let msg = (err.exc || err.message || JSON.stringify(err));
                    frappe.msgprint(msg);
                }
            });


            // -----------------------------------------------------
            //  Add Action Button — Claim Bundle Management
            // -----------------------------------------------------
            listview.page.add_action_item(__('Claim Bundle Management'), async function () {

                let selected_docs = listview.get_checked_items();
                if (!selected_docs.length) {
                    frappe.msgprint(__('Please select at least one claim.'));
                    return;
                }

                let sanctioned_claims = [];

                for (let doc of selected_docs) {
                    let full_doc = await frappe.db.get_doc('Claim', doc.name);

                    if (full_doc.claim_status === "Sanctioned") {
                        sanctioned_claims.push({
                            claim_no: full_doc.name,
                            claim_date: full_doc.claim_date || "",
                            ip_name: full_doc.ip_name || "",
                            ip_no: full_doc.ip_no || "",
                            name_of_patient: full_doc.name_of_patient || "",
                            dispensary: full_doc.dispensary || "",
                            claim_status: full_doc.claim_status || "",
                            amount_claimed: full_doc.amount_claimed || 0,
                            passed_amount: full_doc.passed_amount || 0,
                            ifs_code: full_doc.ifs_code || 0,
                            bank_account_no: full_doc.bank_account_no || 0,
                            bank_name: full_doc.bank_name || 0,
                            ranch: full_doc.branch || 0

                        });
                    }
                }

                if (!sanctioned_claims.length) {
                    frappe.msgprint(__('No selected claims are sanctioned.'));
                    return;
                }

                try {
                    let r = await frappe.call({
                        method: "tqerp_mrcms.api.create_claim_bundle_management",
                        args: { claims_data: JSON.stringify(sanctioned_claims) }
                    });

                    if (r.message?.name) {
                        frappe.set_route("Form", "Claim Bundle Management", r.message.name);
                        frappe.msgprint(__('Claim Bundle Management created.'));
                    }

                } catch (err) {
                    frappe.msgprint(__('Error: {0}', [err.message]));
                }
            });

        } catch (err) {
            console.error("ListView Load Error:", err);
        }
    }
};

frappe.listview_settings['Claim Bundle Management'] = {
    onload: function(listview) {

        listview.page.add_action_item(__('Create Claim Sanction List'), async function () {

            let selected_docs = listview.get_checked_items();
            if (!selected_docs.length) {
                frappe.msgprint(__('Please select at least one record.'));
                return;
            }

            let claims_to_send = [];

            for (let doc of selected_docs) {

                let full_doc = await frappe.call({
                    method: "frappe.client.get",
                    args: {
                        doctype: "Claim Bundle Management",
                        name: doc.name
                    }
                });

                let d = full_doc.message;

                // BLOCK if bundle_status != Sanctioned
                if (d.bundle_status !== "Sanctioned") {
                    frappe.msgprint(`Bundle <b>${d.name}</b> is not Sanctioned. Cannot create sanction list.`);
                    return;
                }

                for (let child of d.details) {
                    claims_to_send.push({
                        claim_bundle_no: d.name,  // <-- assign correct CBM
                        claim_no: child.claim_no,
                        claim_date: child.claim_date || "",
                        ip_name: child.ip_name || "",
                        ip_no: child.ip_no || "",
                        name_of_patient: child.name_of_patient || "",
                        dispensary: child.dispensary || "",
                        claim_status: child.claim_status || "",
                        amount_claimed: child.amount_claimed || 0,
                        passed_amount: child.passed_amount || 0,
                        ifs_code:child.ifs_code || 0,
                        bank_account_no:child.bank_account_no || 0,
                        bank_name:child.bank_name || 0
                    });
                }
            }

            if (!claims_to_send.length) {
                frappe.msgprint(__('No entries found in selected bundles.'));
                return;
            }

            try {
                let r = await frappe.call({
                    method: "tqerp_mrcms.api.create_claim_sanction_list",
                    args: { claims_data: JSON.stringify(claims_to_send) }
                });

                if (r.message?.name) {
                    frappe.msgprint(__('Claim Sanction List created.'));
                    frappe.set_route("Form", "Claim Sanction List", r.message.name);
                }

            } catch (err) {
                frappe.msgprint(__('Error: {0}', [err.message]));
            }
        });
    }
};

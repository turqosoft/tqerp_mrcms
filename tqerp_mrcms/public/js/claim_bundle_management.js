frappe.listview_settings['Claim Bundle Management'] = {
    onload: function(listview) {

        listview.page.add_action_item(__('Create Claim Payment List'), async function () {

            let selected_docs = listview.get_checked_items();
            if (!selected_docs.length) {
                frappe.msgprint(__('Please select at least one record.'));
                return;
            }

            let claims_to_send = [];
            let sections_selected = new Set();

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
                    frappe.msgprint(
                        `Bundle <b>${d.name}</b> is not Sanctioned. Cannot create payment list.`
                    );
                    return;
                }

                // Track sections
                if (d.section) {
                    sections_selected.add(d.section);
                }

                for (let child of d.details) {
                    claims_to_send.push({
                        claim_bundle_no: d.name,
                        claim_no: child.claim_no,
                        claim_date: child.claim_date || "",
                        ip_name: child.ip_name || "",
                        ip_no: child.ip_no || "",
                        name_of_patient: child.name_of_patient || "",
                        dispensary: child.dispensary || "",
                        claim_status: child.claim_status || "",
                        amount_claimed: child.amount_claimed || 0,
                        passed_amount: child.passed_amount || 0,
                        ifs_code: child.ifs_code || "",
                        bank_account_no: child.bank_account_no || "",
                        bank_name: child.bank_name || "",
                        branch: child.branch || "",
                        voucher_no:child.voucher_no
                    });
                }
            }

            // --- BLOCK if multiple sections are selected ---
            if (sections_selected.size > 1) {
                let sections_list = Array.from(sections_selected).join(", ");
                frappe.msgprint(
                    `⚠️ You can't create a Claim Payment List for multiple sections at once. Selected claims belong to: ${sections_list}`
                );
                return;
            }

            if (!claims_to_send.length) {
                frappe.msgprint(__('No entries found in selected bundles.'));
                return;
            }

            try {
                let r = await frappe.call({
                    method: "tqerp_mrcms.api.create_claim_payment_list",
                    args: {
                        claims_data: JSON.stringify(claims_to_send)
                    }
                });

                if (r.message?.name) {
                    frappe.msgprint(__('Claim Payment List created successfully.'));
                    frappe.set_route("Form", "Claim Payment List", r.message.name);
                }

            } catch (err) {
                frappe.msgprint(__('Error: ') + err.message);
            }
        });
    }
};

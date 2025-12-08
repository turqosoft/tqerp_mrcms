frappe.listview_settings['Claim Sanction List'] = {
    onload: function(listview) {

        listview.page.add_action_item(__('Create Claim Payment List'), async function () {

            let selected_docs = listview.get_checked_items();

            if (!selected_docs.length) {
                frappe.msgprint(__('Please select at least one record.'));
                return;
            }

            let payments_to_send = [];

            for (let doc of selected_docs) {

                let full_doc = await frappe.call({
                    method: "frappe.client.get",
                    args: {
                        doctype: "Claim Sanction List",
                        name: doc.name
                    }
                });

                let d = full_doc.message;

                // Sanction status check
                if (d.sanction_status !== "Sanctioned") {
                    frappe.msgprint(
                        `Claim Sanction <b>${d.name}</b> is not Sanctioned. Cannot create payment list.`
                    );
                    return;
                }

                // Child table loop
                for (let child of d.details) {
                    payments_to_send.push({
                        claim_sanction_no: d.name,
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

            if (!payments_to_send.length) {
                frappe.msgprint(__('No entries found in selected sanction lists.'));
                return;
            }

            // Server call
            try {
                let r = await frappe.call({
                    method: "tqerp_mrcms.api.create_claim_payment_list",
                    args: { payments_data: JSON.stringify(payments_to_send) }
                });

                if (r.message?.name) {
                    frappe.msgprint(__('Claim Payment List created.'));
                    frappe.set_route("Form", "Claim Payment List", r.message.name);
                }

            } catch (err) {
                frappe.msgprint(__('Error: {0}', [err.message]));
            }
        });
    }
};

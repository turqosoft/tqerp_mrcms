frappe.ui.form.on("Claim Payment List", {
  
    onload: function(frm) {
        // Set Organisation field of logged in user automatically only if empty
        if (!frm.doc.organisation) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "User",
                    filters: { name: frappe.session.user },
                    fieldname: "organisation"  
                },
                callback: function(r) {
                    if (r && r.message) {
                        frm.set_value("organisation", r.message.organisation);  
                        frm.refresh_field("organisation");

                        // 🔹 Filter Fund Manager based on office
                        // Is this required. Check the commented function above
                    }
                }
            });
        }
    },
    // before_save: function(frm) {
    //     // Calculate total of passed_amount from child table
    //     let total = 0;
    //     if (frm.doc.details && frm.doc.details.length) {
    //         frm.doc.details.forEach(function(row) {
    //             total += row.passed_amount || 0;
    //         });
    //     }
    //     frm.set_value("payment_total", total);
    // },

    refresh: function(frm) {
        // Show Download button ONLY if submitted
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Download List'), function() {
                let d = new frappe.ui.Dialog({
                    title: __('Download Payment List'),
                    fields: [
                        {
                            fieldname: 'file_type',
                            fieldtype: 'Select',
                            label: 'File Type',
                            options: ['Excel', 'CSV'],
                            default: 'Excel',
                            reqd: 1
                        }
                    ],
                    primary_action_label: __('Download'),
                    primary_action(values) {
                        let method = values.file_type === 'CSV'
                            ? "tqerp_mrcms.api.download_payment_details_csv"
                            : "tqerp_mrcms.api.download_payment_details_excel";

                        frappe.call({
                            method: method,
                            args: { docname: frm.doc.name },
                            callback: function(r) {
                                if (r.message) {
                                    window.open(r.message);
                                } else {
                                    frappe.msgprint(__('No file available for download'));
                                }
                            }
                        });

                        d.hide();
                    }
                });
                d.show();
            });


            // -----------------------------
            // UPLOAD PAYMENT BUTTON
            // -----------------------------
            frm.add_custom_button(__('Upload Payment'), function () {

                let d = new frappe.ui.Dialog({
                    title: __('Upload Bank Payment File'),
                    fields: [
                        {
                            fieldname: 'upload_file',
                            fieldtype: 'Attach',
                            label: 'Upload Excel/CSV',
                            reqd: 1
                        }
                    ],
                    primary_action_label: __('Process File'),
                    primary_action(values) {

                        frappe.call({
                            method: "tqerp_mrcms.api.process_payment_file_paymentlist",
                            args: {
                                docname: frm.doc.name,
                                file_url: values.upload_file
                            },
                            freeze: true,
                            freeze_message: "Processing file...",
                            callback: function (r) {
                                if (!r.exc) {

                                    let msg = `
                                        <b>Updated Rows:</b> ${r.message.updated}<br>
                                        <b>Unmatched Rows:</b> ${r.message.unmatched_count}<br>
                                    `;

                                    if (r.message.mismatch_file_url) {
                                        msg += `<br><b>Download Mismatch Report:</b> 
                                                <a href="${r.message.mismatch_file_url}" target="_blank">${r.message.mismatch_file_url}</a>`;
                                    }

                                    frappe.msgprint({
                                        title: __("Payment Upload Summary"),
                                        indicator: r.message.unmatched_count ? "orange" : "green",
                                        message: msg,
                                    });

                                    frm.reload_doc();
                                }
                            }
                        });

                        d.hide();
                    }
                });

                d.show();
            });

        }
    },


    claim_payment_no: frappe.utils.debounce(function(frm) {
        if (!frm.doc.claim_payment_no) return;

        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Claim Payment List',
                filters: { claim_payment_no: frm.doc.claim_payment_no },
                fields: ['name'],
                limit_page_length: 1
            },
            callback: function(r) {
                if (r.message && r.message.length && r.message[0].name !== frm.doc.name) {
                    frappe.msgprint({
                        title: __('Duplicate Value'),
                        message: __('Claim Payment Number already exists'),
                        indicator: 'red'
                    });
                    frm.set_value('claim_payment_no', '');
                }
            }
        });
    }, 300)
});


// ---------------------------------------
// Child Table: Claim Payment Details
// ---------------------------------------
frappe.ui.form.on("Claim Payment Details", {
 
    // Apply filter for claim_no field
    details_add: function(frm, cdt, cdn) {
        frm.fields_dict["details"].grid.get_field("claim_no").get_query = function(doc, cdt, cdn) {
            return {
                filters: {
                    claim_status: "Sanctioned"
                }
            };
        };
    },
 
    // Row added
    details_add: function(frm, cdt, cdn) {
        calculate_payment_total(frm);
    },
 
    // Row removed
    details_remove: function(frm, cdt, cdn) {
        calculate_payment_total(frm);
    },
 
    // Table rendered
    details_on_form_rendered: function(frm, cdt, cdn) {
        calculate_payment_total(frm);
    },
 
    // Trigger whenever passed_amount is fetched/changed
    passed_amount: function(frm, cdt, cdn) {
        calculate_payment_total(frm);
    },
 
   
    claim_no: function(frm, cdt, cdn) {
        calculate_payment_total(frm);
    },
 
    // Row removed from child table
    details_remove: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.claim_no) return;
 
        // 1️⃣ Clear CPL link from the Claim
        frappe.call({
            method: "frappe.client.set_value",
            args: {
                doctype: "Claim",
                name: row.claim_no,
                fieldname: "claim_payment_list",
                value: ""
            },
            callback: function() {
                // Show browser message for testing
                frappe.msgprint(`✅ Claim Payment List link removed from Claim: <b>${row.claim_no}</b>`);
 
             
            }
        });
 
        // 2️⃣ Update bundle status for the related Claim Bundle
        if (row.claim_bundle_no) {
            frappe.call({
                method: "tqerp_mrcms.api.update_bundle_status",
                args: { bundle_name: row.claim_bundle_no }
            });
        }
    },
 
 
});
 
function calculate_payment_total(frm) {
    let total = 0.0;
    let bundles = {};
 
    (frm.doc.details || []).forEach(row => {
        if(row.claim_bundle_no) bundles[row.claim_bundle_no] = true;
    });
 
    for(let bundle_no in bundles){
        frappe.call({
            method: "frappe.client.get_list",
            async: false,  // synchronous call to wait for result
            args: {
                doctype: "Claim Bundle Details",
                filters: { parent: bundle_no },
                fields: ["passed_amount"]
            },
            callback: function(r) {
                r.message.forEach(d => {
                    total += flt(d.passed_amount, 2);
                });
            }
        });
    }
 
    frm.set_value("payment_total", total);
}

frappe.ui.form.on("Claim Payment List", {
    onload: function(frm) {
        // Auto-set Office from logged-in user
        if (!frm.doc.office) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "User",
                    filters: { name: frappe.session.user },
                    fieldname: "office"
                },
                callback: function(r) {
                    if (r && r.message) {
                        frm.set_value("office", r.message.office);
                        frm.refresh_field("office");
                    }
                }
            });
        }
    },

    before_save: function(frm) {
        // Calculate total of passed_amount from child table
        let total = 0;
        if (frm.doc.details && frm.doc.details.length) {
            frm.doc.details.forEach(function(row) {
                total += row.passed_amount || 0;
            });
        }
        frm.set_value("payment_total", total);
    },

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
    }
});

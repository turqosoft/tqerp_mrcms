frappe.ui.form.on('Claim Proceedings', {

    onload: function(frm) {
        // Autofill total_allocated with default value if exists
        if(frm.doc.total_allocated) {
            frm.set_value("total_allocated", frm.doc.total_allocated);
        }

        // Dynamically filter fund_manager based on office
        frm.set_query("fund_manager", function() {
            if (!frm.doc.office) {
                frappe.msgprint("Please select Office first.");
                return {};
            }
            return {
                query: "tqerp_mrcms.api.get_available_fund_managers",
                filters: { office: frm.doc.office }
            };
        });
    },

    // When fund_manager is selected, fetch fund details
    fund_manager: function(frm) {
        if (!frm.doc.fund_manager) return;

        console.log("Fetching fund details for Fund Manager:", frm.doc.fund_manager);

        frappe.call({
            method: "tqerp_mrcms.api.get_fund_details",
            args: { fund_manager: frm.doc.fund_manager, office: frm.doc.office },
            callback: function(r) {
                if(r.message) {
                    frm.set_value("available", r.message.available);
                    frm.set_value("balance", r.message.available);
                    frm.set_value("fund_date", r.message.fund_date);

                    if (r.message.approval_note) {
                        frm.set_value("approval_note", r.message.approval_note);
                        frm.toggle_display("approval_note", true);
                    } else {
                        frm.set_value("approval_note", "");
                        frm.toggle_display("approval_note", false);
                    }
                }
            }
        });
    },

    refresh: function(frm) {
        // Fetch Fund Manager details
        if(frm.doc.fund_manager) {
            frappe.call({
                method: "tqerp_mrcms.api.get_fund_details",
                args: { fund_manager: frm.doc.fund_manager, office: frm.doc.office },
                callback: function(r) {
                    if(r.message) {
                        frm.set_value("available", r.message.available);
                        frm.set_value("balance", r.message.available);
                        frm.set_value("fund_date", r.message.fund_date);

                        if(r.message.approval_note) {
                            frm.set_value("approval_note", r.message.approval_note);
                            frm.toggle_display("approval_note", true);
                        } else {
                            frm.set_value("approval_note", "");
                            frm.toggle_display("approval_note", false);
                        }
                    }
                }
            });
        }

        // ✅ Sum passed_amount from child table into total_allocated
        let total = 0;
        if(frm.doc.claim_proceedings && frm.doc.claim_proceedings.length) {
            frm.doc.claim_proceedings.forEach(row => {
                total += flt(row.passed_amount || 0);
            });
        }
        frm.set_value("total_allocated", total);
    },

    validate: function(frm) {
        if(frm.doc.total_allocated && frm.doc.available) {
            if(flt(frm.doc.total_allocated) > flt(frm.doc.available)) {
                frappe.throw(`Total Allocated (${frm.doc.total_allocated}) cannot exceed Available Fund (${frm.doc.available}).`);
            }
        }
    },

    before_submit: function(frm) {
        if(flt(frm.doc.total_allocated) > flt(frm.doc.available)) {
            frappe.throw(`Cannot submit. Total Allocated (${frm.doc.total_allocated}) is greater than Available Fund (${frm.doc.available}).`);
        }

        frappe.call({
            method: "tqerp_mrcms.api.allocate_fund_on_submit",
            args: { docname: frm.doc.name, doctype: "Claim Proceedings" },
            async: false,
            callback: function(r) {
                frappe.msgprint("Fund allocation updated successfully.");
                frm.reload_doc();
            }
        });
    },

    before_cancel: function(frm) {
        frappe.call({
            method: "tqerp_mrcms.api.reverse_fund_on_cancel",
            args: { payment_list_name: frm.doc.name },
            async: false,
            callback: function(r) {
                frappe.msgprint("Fund reversed back successfully.");
            }
        });
    }

});

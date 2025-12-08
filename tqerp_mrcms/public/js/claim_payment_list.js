frappe.ui.form.on('Claim Payment List', {
    onload: function(frm) {
        // Autofill total_allocated with payment_total
        if(frm.doc.payment_total) {
            frm.set_value("total_allocated", frm.doc.payment_total);
        }
    },

    refresh: function(frm) {
        // Button to fetch available fund
        frm.add_custom_button(__('Check Fund Available'), function() {
            if (!frm.doc.office) {
                frappe.msgprint(__('Office not set.'));
                return;
            }

            frappe.call({
                method: "tqerp_mrcms.api.get_fixed_fund_for_office",
                args: { office: frm.doc.office },
                callback: function(r) {
                    if (r.message !== undefined) {
                        frm.set_value("available", r.message.fixed);
                        frm.set_value("balance", r.message.fixed);
                        frappe.msgprint(__('Available fund for this office: {0}', [r.message.fixed]));
                    }
                }
            });
        });

        // Also autofill total_allocated when refreshing
        if(frm.doc.payment_total) {
            frm.set_value("total_allocated", frm.doc.payment_total);
        }
    },

    before_submit: function(frm) {
        // Automatically allocate fund on submit
        frappe.call({
            method: "tqerp_mrcms.api.allocate_fund_on_submit",
            args: { payment_list_name: frm.doc.name },
            async: false,
            callback: function(r) {
                frappe.msgprint(__('Fund allocation updated successfully.'));
                frm.reload_doc();
            }
        });
    }
});

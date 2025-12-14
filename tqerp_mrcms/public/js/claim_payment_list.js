frappe.ui.form.on('Claim Payment List', {
    onload: function(frm) {
        // Autofill total_allocated with payment_total
        if(frm.doc.payment_total) {
            frm.set_value("total_allocated", frm.doc.payment_total);
        }
        
        //✅ Dynamically filter fund_manager based on office
        frm.set_query("fund_manager", function() {
            if (!frm.doc.office) {
                frappe.msgprint("Please select Office first.");
                return {};
            }
        
            return {
                query: "tqerp_mrcms.api.get_available_fund_managers",
                filters: {
                    office: frm.doc.office
                }
            };
        });
    },

    

     //✅ When user selects a Fund Manager → Auto fetch details
     fund_manager: function(frm) {
        if (!frm.doc.fund_manager) return;
    
        frappe.call({
            method: "tqerp_mrcms.api.get_fund_details",
            args: { fund_manager: frm.doc.fund_manager, office: frm.doc.office },
            callback: function(r) {
                if (r.message) {
    
                    frm.set_value("available", r.message.available);
                    frm.set_value("balance", r.message.available);
                    frm.set_value("fund_date", r.message.fund_date);
    
                    // Show only when approval note exists
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
    
    
    // On refresh, also update balance from current Fund Manager
    refresh: function(frm) {
    if(frm.doc.fund_manager) {

        frappe.call({
            method: "tqerp_mrcms.api.get_fund_details",
            args: { fund_manager: frm.doc.fund_manager, office: frm.doc.office },
            callback: function(r) {
                if(r.message) {

                    frm.set_value("available", r.message.available);
                    frm.set_value("balance", r.message.available);
                    frm.set_value("fund_date", r.message.fund_date);

                    // ⭐ Show only when approval note exists
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
    }

    if(frm.doc.payment_total) {
        frm.set_value("total_allocated", frm.doc.payment_total);
    }
},

    

    //  VALIDATION BEFORE SAVE
    validate: function(frm) {
        if (frm.doc.total_allocated && frm.doc.available) {
            if (flt(frm.doc.total_allocated) > flt(frm.doc.available)) {
                frappe.throw(
                    __("Total Allocated Amount ({0}) cannot exceed Available Fund ({1}).", 
                    [frm.doc.total_allocated, frm.doc.available])
                );
            }
        }
    },


    // BLOCK SUBMIT IF ALLOCATION > AVAILABLE
    before_submit: function(frm) {
        if (flt(frm.doc.total_allocated) > flt(frm.doc.available)) {
            frappe.throw(
                __("You cannot submit. Total Allocated ({0}) is greater than Available Fund ({1}).", 
                [frm.doc.total_allocated, frm.doc.available])
            );
        }

        // ✅ Updated call to generic API
        frappe.call({
            method: "tqerp_mrcms.api.allocate_fund_on_submit",
            args: { 
                docname: frm.doc.name,
                doctype: "Claim Payment List"
            },
            async: false,
            callback: function(r) {
                frappe.msgprint(__('Fund allocation updated successfully.'));
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
                frappe.msgprint(__('Fund reversed back successfully.'));
            }
        });
    }
});

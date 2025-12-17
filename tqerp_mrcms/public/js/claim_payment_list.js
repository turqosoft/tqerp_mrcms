frappe.ui.form.on('Claim Payment List', {

    setup: function(frm) {
        frm.set_query("fund_manager", function() {
            return {
                query: "tqerp_mrcms.api.get_available_fund_managers",
                filters: { office: frm.doc.office }
            };
        });
    },
    
    onload: function(frm) {

       
        if (!frm.is_new()) return;
    
        // Get logged-in user's office
        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "User",
                filters: { name: frappe.session.user },
                fieldname: ["office"]
            },
            callback: function(r) {
                if (r.message && r.message.office && !frm.doc.office) {
    
                    // ✅ silent set (safe only for new doc)
                    frm.doc.office = r.message.office;
                    frm.refresh_field("office");
                }
            }
        });
    
        // Silent autofill total_allocated (NEW DOC ONLY)
        if (frm.doc.payment_total && !frm.doc.total_allocated) {
            frm.doc.total_allocated = frm.doc.payment_total;
            frm.refresh_field("total_allocated");
        }
    },
    
    

    // -------------------------------
    // FUND MANAGER SELECT (DRAFT ONLY)
    // -------------------------------
    fund_manager: function(frm) {

        if(!frm.doc.fund_manager || frm.doc.docstatus === 1) return;

        // Use automatically set office
        fetch_fund_details(frm, frm.doc.office);
    },

    // -------------------------------
    // TOTAL ALLOCATED CHANGE (DRAFT)
    // -------------------------------
    total_allocated: function(frm) {
        if(frm.doc.docstatus === 1) return;

        if(frm.doc.available) {
            frm.set_value(
                "balance",
                flt(frm.doc.available) - flt(frm.doc.total_allocated || 0)
            );
        }
    },
    

    
    refresh: function(frm) {

        // AFTER SUBMIT → DO NOTHING
        if (frm.doc.docstatus === 1) return;
    
        // Only autofill ONCE (new OR unsaved draft)
        if (!frm.doc.__total_allocated_filled &&
            frm.doc.payment_total &&
            !frm.doc.total_allocated) {
    
            frm.set_value("total_allocated", frm.doc.payment_total);
            frm.doc.__total_allocated_filled = true;
        }
    
        // Fund calc only for NEW doc
        if (frm.is_new() && frm.doc.fund_manager && frm.doc.office) {
            fetch_fund_details(frm, frm.doc.office);
        }
    },       

    // -------------------------------
    // VALIDATION
    // -------------------------------
    validate: function(frm) {
        if(frm.doc.total_allocated && frm.doc.available &&
           flt(frm.doc.total_allocated) > flt(frm.doc.available)) {
            frappe.throw(
                __("Total Allocated ({0}) cannot exceed Available Fund ({1})",
                    [frm.doc.total_allocated, frm.doc.available])
            );
        }
    },

   
    before_submit: function(frm) {
        return new Promise((resolve, reject) => {
            frappe.call({
                method: "tqerp_mrcms.api.allocate_fund_on_submit",
                args: {
                    docname: frm.doc.name,
                    doctype: "Claim Payment List"
                },
                callback: function(r) {
                    resolve(); // ✅ allow submit
                },
                error: function(err) {
                    // Server already sent message via frappe.throw
                    // Just block submit
                    reject();
                }
            });
        });
    }
    

    // -------------------------------
    // BEFORE CANCEL
    // -------------------------------
    // before_cancel: function(frm) {
    //     frappe.call({
    //         method: "tqerp_mrcms.api.reverse_fund_on_cancel",
    //         args: { payment_list_name: frm.doc.name },
    //         async: false
    //     });
    // }
});

// ===============================
// HELPER FUNCTION
// ===============================
function fetch_fund_details(frm, office) {

    frappe.call({
        method: "tqerp_mrcms.api.get_fund_details",
        args: { 
            fund_manager: frm.doc.fund_manager,
            office: office // automatically use logged-in user's office
        },
        callback: function(r) {
            if(!r.message) return;

            // Available = Fixed − Allocated (SOURCE OF TRUTH)
            frm.set_value("available", r.message.available);

            // Balance = Available − Current Allocation
            frm.set_value(
                "balance",
                flt(r.message.available) - flt(frm.doc.total_allocated || 0)
            );

            frm.set_value("fund_date", r.message.fund_date);

            if(r.message.approval_note) {
                frm.set_value("approval_note", r.message.approval_note);
                frm.toggle_display("approval_note", true);
            } else {
                frm.toggle_display("approval_note", false);
            }
        }
    });
}

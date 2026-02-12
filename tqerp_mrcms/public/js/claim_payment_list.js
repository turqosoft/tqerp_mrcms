frappe.ui.form.on('Claim Payment List', {

    setup: function(frm) {
        frm.set_query("fund_manager", function() {
            return {
                query: "tqerp_mrcms.api.get_available_fund_managers",
                filters: {
                    organisation: frm.doc.organisation,
                    expired: 0
                }
            };
        });
    },
    after_save(frm) {
        // ✅ Guard using REAL field
        if (frm.doc.payment_status === "Paid") {
            return;
        }
 
        frappe.call({
            method: "tqerp_mrcms.api.allocate_fund_on_submit",
            args: {
                docname: frm.doc.name,
                doctype: "Claim Payment List"
            },
            callback(r) {
                if (!r.exc) {
                    frm.reload_doc(); // refresh balances + status
                }
            }
        });
    },
    onload: function(frm) {

        if (!frm.is_new()) return;
    
        // Get logged-in user's organisation
        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "User",
                filters: { name: frappe.session.user },
                fieldname: ["organisation"]
            },
            callback: function(r) {
                if (r.message && r.message.organisation && !frm.doc.organisation) {

                    
                    frm.doc.organisation = r.message.organisation;
                    frm.refresh_field("organisation");
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

        // Use automatically set organisation
        fetch_fund_details(frm, frm.doc.organisation);
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
        // if (!frm.doc.__total_allocated_filled &&
        //     frm.doc.payment_total &&
        //     !frm.doc.total_allocated) {
    
        //     frm.set_value("total_allocated", frm.doc.payment_total);
        //     frm.doc.__total_allocated_filled = true;
        // }
    
        // Fund calc only for NEW doc
        if (frm.is_new() && frm.doc.fund_manager && frm.doc.organisation) {
            fetch_fund_details(frm, frm.doc.organisation);
        }
    },       
    validate: function(frm) {
        //  ONE source of truth
        if (
            frm.doc.payment_total &&
            !frm.doc.total_allocated
        ) {
            frm.doc.total_allocated = frm.doc.payment_total;
        }
 
        // Allocation safety check
        if (
            frm.doc.total_allocated &&
            frm.doc.available &&
            flt(frm.doc.total_allocated) > flt(frm.doc.available)
        ) {
            frappe.throw(
                __("Total Allocated ({0}) cannot exceed Available Fund ({1})", [
                    frm.doc.total_allocated,
                    frm.doc.available
                ])
            );
        }
 
        if(frm.doc.total_allocated && frm.doc.available &&
           flt(frm.doc.total_allocated) > flt(frm.doc.available)) {
            frappe.throw(
                __("Total Allocated ({0}) cannot exceed Available Fund ({1})",
                    [frm.doc.total_allocated, frm.doc.available])
            );
        }
    },
    before_workflow_action: async function (frm) {
        // Return the promise here!
        return new Promise((resolve, reject) => {
            frappe.dom.unfreeze()
            frappe.confirm(
                `<b>Are you sure you want to <u>${frm.selected_workflow_action}</u>?</b>`,
                () => resolve(), // Yes → proceed
                () => reject("❌ Action cancelled by user.") // No → abort transition
            );
        });
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

    
});

// ===============================
// HELPER FUNCTION
// ===============================
function fetch_fund_details(frm, organisation) {

    frappe.call({
        method: "tqerp_mrcms.api.get_fund_details",
        args: { 
            fund_manager: frm.doc.fund_manager,
            organisation: organisation // automatically use logged-in user's organisation
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

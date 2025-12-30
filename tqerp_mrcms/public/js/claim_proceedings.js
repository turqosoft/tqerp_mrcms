frappe.ui.form.on('Claim Proceedings', {

    // -------------------------------
    // ONLOAD
    // -------------------------------
    onload: function(frm) {

        // 🔹 Auto-set Organisation from logged-in user
        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "User",
                filters: { name: frappe.session.user },
                fieldname: ["organisation"]
            },
            callback: function(r) {
                if (r.message && r.message.organisation) {

                    frm.set_value("organisation", r.message.organisation);

                    // 🔹 Filter Fund Manager based on organisation
                    frm.set_query("fund_manager", function() {
                        return {
                            query: "tqerp_mrcms.api.get_available_fund_managers",
                            filters: { organisation: r.message.organisation }
                        };
                    });

                    // 🔹 Fetch fund details if already selected
                    if (frm.doc.fund_manager && frm.doc.docstatus === 0) {
                        fetch_fund_details(frm);
                    }
                }
            }
        });
    },

    // -------------------------------
    // FUND MANAGER CHANGE (DRAFT ONLY)
    // -------------------------------
    fund_manager: function(frm) {
        if (!frm.doc.fund_manager || frm.doc.docstatus === 1) return;
        fetch_fund_details(frm);
    },

    // -------------------------------
    // CHILD TABLE CHANGE
    // -------------------------------
    claim_proceedings_add: update_total,
    claim_proceedings_remove: update_total,

    // -------------------------------
    // REFRESH
    // -------------------------------
    refresh: function(frm) {

        // 🔒 AFTER SUBMIT → NO UI LOGIC
        if (frm.doc.docstatus === 1) return;

        if (frm.doc.fund_manager && frm.doc.organisation) {
            fetch_fund_details(frm);
        }

        update_total(frm);
    },

    // -------------------------------
    // VALIDATION
    // -------------------------------
    validate: function(frm) {
        if (
            frm.doc.total_allocated &&
            frm.doc.available &&
            flt(frm.doc.total_allocated) > flt(frm.doc.available)
        ) {
            frappe.throw(
                __("Total Allocated ({0}) cannot exceed Available Fund ({1})",
                    [frm.doc.total_allocated, frm.doc.available])
            );
        }
    },

    // -------------------------------
    // BEFORE SUBMIT
    // -------------------------------
    before_submit: function(frm) {

        if (flt(frm.doc.total_allocated) > flt(frm.doc.available)) {
            frappe.throw(
                __("Cannot submit. Total Allocated ({0}) is greater than Available Fund ({1})",
                    [frm.doc.total_allocated, frm.doc.available])
            );
        }

        frappe.call({
            method: "tqerp_mrcms.api.allocate_fund_on_submit",
            args: {
                docname: frm.doc.name,
                doctype: "Claim Proceedings"
            },
            async: false
        });
    }
});


// ======================================
// HELPER FUNCTIONS
// ======================================

function update_total(frm) {

    let total = 0;

    if (frm.doc.claim_proceedings) {
        frm.doc.claim_proceedings.forEach(row => {
            total += flt(row.passed_amount || 0);
        });
    }

    frm.set_value("total_allocated", total);

    if (frm.doc.available) {
        frm.set_value(
            "balance",
            flt(frm.doc.available) - flt(total)
        );
    }
}

function fetch_fund_details(frm) {

    frappe.call({
        method: "tqerp_mrcms.api.get_fund_details",
        args: {
            fund_manager: frm.doc.fund_manager,
            organisation: frm.doc.organisation
        },
        callback: function(r) {

            if (!r.message) return;

            // 🔹 Source of truth
            frm.set_value("available", r.message.available);

            frm.set_value(
                "balance",
                flt(r.message.available) - flt(frm.doc.total_allocated || 0)
            );

            frm.set_value("fund_date", r.message.fund_date);

            if (r.message.approval_note) {
                frm.set_value("approval_note", r.message.approval_note);
                frm.toggle_display("approval_note", true);
            } else {
                frm.toggle_display("approval_note", false);
            }
        }
    });
}

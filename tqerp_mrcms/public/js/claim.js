// ------------------------------
// Parent Doctype (Claim)
// ------------------------------
frappe.ui.form.on("Claim", {

    refresh(frm) {
        // Convert passed_amount to words on refresh if already set
        if (frm.doc.passed_amount) {
            frm.trigger("passed_amount");
        }
    },

    before_workflow_action: async function (frm) {
        return new Promise((resolve, reject) => {
            frappe.dom.unfreeze();
            frappe.confirm(
                `<b>Are you sure you want to <u>${frm.selected_workflow_action}</u>?</b>`,
                () => resolve(), // Yes → proceed
                () => reject("❌ Action cancelled by user.") // No → abort
            );
        });
    },

    validate(frm) {
        calculate_total_bill_amount(frm);
        calculat_bill_total_passed_amount(frm);
    },

    // Convert parent passed_amount to words
    passed_amount(frm) {
        if (!frm.doc.passed_amount) {
            frm.set_value("rupees", "");
            return;
        }

        frappe.call({
            method: "tqerp_mrcms.api.number_to_words_indian",
            args: { num: frm.doc.passed_amount },
            callback(r) {
                if (r.message) {
                    frm.set_value("rupees", r.message);
                }
            },
            error(err) {
                console.error("Error converting number to words:", err);
            }
        });
    }
});


// ------------------------------
// Child Table Events (Bill Details)
// ------------------------------
frappe.ui.form.on("Bill Details", {

    bill_amount(frm, cdt, cdn) {
        calculate_total_bill_amount(frm);
    },

    passed_amount(frm, cdt, cdn) {
        calculat_bill_total_passed_amount(frm);
    },

    bill_details_remove(frm, cdt, cdn) {
        calculate_total_bill_amount(frm);
        calculat_bill_total_passed_amount(frm);
    }
});


// ------------------------------
// Calculate Total Bill Amount
// ------------------------------
function calculate_total_bill_amount(frm) {
    let total = 0;

    (frm.doc.bill_details || []).forEach(row => {
        total += flt(row.bill_amount);
    });

    frm.set_value("bill_total", total);
}


// ------------------------------
// Calculate Total Passed Amount
// ------------------------------
function calculat_bill_total_passed_amount(frm) {
    let total = 0;

    (frm.doc.bill_details || []).forEach(row => {
        total += flt(row.passed_amount);
    });

    frm.set_value("bill_total_passed_amount", total);
}

// ------------------------------
// Parent Doctype (Claim)
// ------------------------------
frappe.ui.form.on("Claim", {

    refresh(frm) {
        // console.log("Claim Form: refresh triggered");
        // Convert passed_amount to rupees on refresh if already set
        if (frm.doc.passed_amount) frm.trigger("passed_amount");
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
    validate(frm) {
        // console.log("Claim Form: validate triggered");
        calculate_total_bill_amount(frm);
    },

    // Trigger when passed_amount field changes
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
        // console.log("Bill Details: bill_amount changed", cdt, cdn);
        calculate_total_bill_amount(frm);
    },

    bill_details_remove(frm, cdt, cdn) {
        // console.log("Bill Details: row removed", cdt, cdn);
        calculate_total_bill_amount(frm);
    }
});

// ------------------------------
// Calculate Total Amount
// ------------------------------
function calculate_total_bill_amount(frm) {
    // console.log("Calculating total bill amount...");

    let total = 0;

    (frm.doc.bill_details || []).forEach(row => {
        // console.log("Row bill_amount:", row.bill_amount);
        total += flt(row.bill_amount);
    });

    // console.log("Total calculated:", total);
    frm.set_value("bill_total", total);
}

frappe.ui.form.on("Claim Sanction List", {
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
        frm.set_value("sanction_total", total);
    }
});

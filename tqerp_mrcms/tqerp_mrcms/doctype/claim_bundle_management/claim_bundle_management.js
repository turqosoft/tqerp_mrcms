// -------------------------------
// Claim Bundle Management (Parent)
// -------------------------------
frappe.ui.form.on("Claim Bundle Management", {
    onload: function(frm) {
        // Set Organisation field automatically only if empty
        if (!frm.doc.organisation) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "User",
                    filters: { name: frappe.session.user },
                    fieldname: "organisation"  
                },
                callback: function(r) {
                    if (r && r.message) {
                        frm.set_value("organisation", r.message.organisation);  
                        frm.refresh_field("organisation");  
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
        frm.set_value("bundle_total", total);
    }
});
    

// ---------------------------------------
// Child Table: Claim Bundle Details
// Apply filter for claim_no field
// ---------------------------------------
frappe.ui.form.on("Claim Bundle Details", {
    
    details_add: function(frm, cdt, cdn) {
        // Only show claims where claim_status = "Sanctioned"
        frm.fields_dict["details"].grid.get_field("claim_no").get_query = function(doc, cdt, cdn) {
            return {
                filters: {
                    claim_status: "Sanctioned"
                }
            };
        };
    }

});

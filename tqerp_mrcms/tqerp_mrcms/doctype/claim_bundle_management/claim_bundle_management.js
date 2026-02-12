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
    // before_save: function(frm) {
    //     // Calculate total of passed_amount from child table
    //     let total = 0;
    //     if (frm.doc.details && frm.doc.details.length) {
    //         frm.doc.details.forEach(function(row) {
    //             total += row.passed_amount || 0;
    //         });
    //     }
    //     frm.set_value("bundle_total", total);
    // },


    physical_bundle_no: frappe.utils.debounce(function(frm) {
            if (!frm.doc.physical_bundle_no) return;
    
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Claim Bundle Management',
                    filters: { physical_bundle_no: frm.doc.physical_bundle_no },
                    fields: ['name'],
                    limit_page_length: 1
                },
                callback: function(r) {
                    if (r.message && r.message.length && r.message[0].name !== frm.doc.name) {
                        frappe.msgprint({
                            title: __('Duplicate Value'),
                            message: __('Physical Bundle Number already exists'),
                            indicator: 'red'
                        });
                        frm.set_value('physical_bundle_no', '');
                    }
                }
            });
        }, 300),

    
    
});
    

// ---------------------------------------
// Child Table: Claim Bundle Details
// Apply filter for claim_no field
// ---------------------------------------
// --------------------------------------
frappe.ui.form.on("Claim Bundle Details", {
    details_add: function(frm, cdt, cdn) {
        frm.fields_dict["details"].grid.get_field("claim_no").get_query = function(doc, cdt, cdn) {
            return {
                filters: {
                    claim_status: "Sanctioned",
                    claim_category: ["in", [" Category C1", "Category C2", "Category D"]]
                }
            };
        };
        calculate_bundle_total(frm);
    },
 
   
    // Row removed
    details_remove: function(frm, cdt, cdn) {
        calculate_bundle_total(frm);
    },
    // Table rendered (optional)
    details_on_form_rendered: function(frm, cdt, cdn) {
        calculate_bundle_total(frm);
    },
    // Trigger whenever passed_amount is changed
    passed_amount: function(frm, cdt, cdn) {
        calculate_bundle_total(frm);
    }
});
 
// function to sum 'passed_amount' from table and set 'bundle_total'
function calculate_bundle_total(frm) {
    let total = 0.0;
    frm.doc.details.forEach(row => {
        total += flt(row.passed_amount, 2); // convert to float, 2 decimals
    });
    frm.set_value('bundle_total', total);
   
}
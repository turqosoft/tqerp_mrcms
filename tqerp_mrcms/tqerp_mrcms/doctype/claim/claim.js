frappe.ui.form.on('Claim', {
    claim_templates: function(frm) {
        if (frm.doc.claim_templates) {
            frappe.db.get_doc('Claim Checklist', frm.doc.claim_templates)
                .then(doc => {
                    // Clear existing claim_checklist table
                    frm.clear_table('claim_checklist');

                    // Loop through claim_checklist_details in Claim Checklist
                    (doc.claim_checklist_details || []).forEach(row => {
                        let child = frm.add_child('claim_checklist');
                        child.criteria = row.criteria;
                        child.required = row.required;
                        child.presen = row.presen;
                    });

                    // Refresh the field to display new rows
                    frm.refresh_field('claim_checklist');
                });
        } else {
            // If Claim Template is cleared, empty the checklist
            frm.clear_table('claim_checklist');
            frm.refresh_field('claim_checklist');
        }
    }
});

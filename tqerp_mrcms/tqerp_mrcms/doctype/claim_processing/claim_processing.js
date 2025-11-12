frappe.ui.form.on('Claim Processing', {
    claim_templates: function(frm) {
        if (frm.doc.claim_templates) {
            frappe.db.get_doc('Claim Checklist', frm.doc.claim_templates)
                .then(doc => {
                    if (!doc.claim_checklist_details || !doc.claim_checklist_details.length) {
                        frappe.msgprint(__('No checklist details found in the selected Claim Template.'));
                        return;
                    }

                    // Clear existing rows
                    frm.clear_table('claim_checklist');

                    // Add new rows
                    doc.claim_checklist_details.forEach(row => {
                        let child = frm.add_child('claim_checklist');
                        child.criteria = row.criteria;
                        child.required = row.required;
                        child.presen = row.presen;
                    });

                    frm.refresh_field('claim_checklist');
                })
                .catch(err => {
                    frappe.msgprint(__('Failed to fetch Claim Checklist details.'));
                    console.error(err);
                });
        } else {
            // If no template selected, clear the checklist
            frm.clear_table('claim_checklist');
            frm.refresh_field('claim_checklist');
        }
    }
});

frappe.ui.form.on('Claim', {
    claim_templates: function(frm) {
        load_claim_checklist(frm);
    },
 
    onload: function(frm) {
        // Load default checklist only if no template is selected
        if (!frm.doc.claim_templates) {
            load_claim_checklist(frm, true);
        }
 
        // Make the child table fields read-only in Claim
        make_claim_checklist_readonly(frm);
    }
});
 
// 🔹 Helper function to load claim checklist
function load_claim_checklist(frm, use_default = false) {
    let template_name = frm.doc.claim_templates;
 
    // If no template and use_default is true → get from MRCMS Settings
    if (!template_name && use_default) {
        frappe.db.get_single_value('MRCMS Settings', 'default_claim_checklist')
            .then(default_template => {
                if (default_template) {
                    frm.set_value('claim_templates', default_template);
                    frm.refresh_field('claim_templates');
 
                    // Then load checklist from that template
                    frappe.db.get_doc('Claim Checklist', default_template)
                        .then(doc => {
                            populate_claim_checklist(frm, doc);
                        });
                }
            });
    }
    else if (template_name) {
        frappe.db.get_doc('Claim Checklist', template_name)
            .then(doc => {
                populate_claim_checklist(frm, doc);
            });
    }
    else {
        // Clear if neither selected nor default
        frm.clear_table('claim_checklist');
        frm.refresh_field('claim_checklist');
    }
}
 
// 🔹 Populate checklist rows
function populate_claim_checklist(frm, doc) {
    frm.clear_table('claim_checklist');
 
    (doc.claim_checklist_details || []).forEach(row => {
        let child = frm.add_child('claim_checklist');
        child.criteria = row.criteria;
        child.required = row.required;
        child.present = row.present;
    });
 
    frm.refresh_field('claim_checklist');
 
    // After populating, make fields read-only
    make_claim_checklist_readonly(frm);
}
 
//  Make the checklist fields read-only in Claim only
function make_claim_checklist_readonly(frm) {
    // Make grid fields readonly
    const grid = frm.get_field('claim_checklist').grid;
    ['criteria', 'required', ].forEach(fieldname => {
        frappe.meta.get_docfield('Claim Checklist Details', fieldname, frm.doc.name).read_only = 1;
    });
 
    // Prevent adding or deleting rows
    grid.cannot_add_rows = true;
    grid.cannot_delete_rows = true;
    grid.only_sortable = false;
 
    frm.refresh_field('claim_checklist');
 
    // Wait until grid is rendered, then hide "Add Row"
    setTimeout(() => {
        $(frm.fields_dict.claim_checklist.grid.wrapper)
            .find('.grid-add-row, .grid-footer, .grid-empty')
            .hide();
    }, 300);
}
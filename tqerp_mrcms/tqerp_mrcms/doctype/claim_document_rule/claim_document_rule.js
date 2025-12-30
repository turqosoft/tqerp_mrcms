frappe.ui.form.on('Claim Document Rule', {
    refresh(frm) {

        if (frm.fields_dict.claim_document_rule_details) {

            frm.fields_dict.claim_document_rule_details.grid
                .get_field('claim_doc_master')
                .get_query = function () {

                    return {
                        filters: {
                            is_active: 1    // Active only
                        }
                    };
                };
        }
    }
});

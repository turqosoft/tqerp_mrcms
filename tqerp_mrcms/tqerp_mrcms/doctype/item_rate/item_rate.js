frappe.ui.form.on('Item Rate', {
    setup(frm) {
        frm.set_query('item_code', function () {
            return {
                query: 'tqerp_mrcms.api.item_code_with_name'
            };
        });
    }
    // rate_list(frm) {
    //     if (!frm.doc.rate_list) return;

    //     frappe.db.get_value(
    //         'Rate List',
    //         frm.doc.rate_list,
    //         ['effective_from', 'is_active']
    //     ).then(r => {
    //         if (r.message) {
    //             frm.set_value('effective_from', r.message.effective_from);
    //             frm.set_value('is_active', r.message.is_active);
    //         }
    //     });
    // }
});

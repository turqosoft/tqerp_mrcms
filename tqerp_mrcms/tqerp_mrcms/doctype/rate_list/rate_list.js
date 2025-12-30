frappe.ui.form.on('Rate List', {
    refresh(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(
                __('Add / Edit Item Rate List'),
                () => {
                    frappe.set_route('List', 'Item Rate List', {
                        rate_list: frm.doc.name
                    });
                },
                __('Actions')
            );
        }
    }
});

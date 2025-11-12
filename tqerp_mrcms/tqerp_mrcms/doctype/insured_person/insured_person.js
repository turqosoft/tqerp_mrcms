// Parent doctype events (Insured Person)
frappe.ui.form.on('Insured Person', {

    refresh: function(frm) {
        frm.set_query("dispensary", function() {
            return {
                filters: {
                    type: "Dispensary"
                }
            };
        });
    },

   
});

// Parent doctype events (Insured Person)
frappe.ui.form.on('Insured Person', {

    refresh: function(frm) {
        frm.set_query("dispensary", function() {
            return {
                filters: {
                    type: "Dispensery"
                }
            };
        });
        frm.set_query("local_office", function() {
            return {
                filters: {
                    type: "Regional Director Office"
                }
            };
        });
    },

   
});

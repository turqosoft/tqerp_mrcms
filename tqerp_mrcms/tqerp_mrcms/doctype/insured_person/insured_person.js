// Parent doctype events (Insured Person)
frappe.ui.form.on('Insured Person', {

    refresh: function(frm) {

        // Existing dispensary filter
        frm.set_query("dispensary", function() {
            return {
                filters: {
                    type: "Dispensary"
                }
            };
        });

        // 👉 Add Create Claim Button
        if (!frm.is_new()) {
            frm.add_custom_button('Create Claim', function() {
                
                frappe.call({
                    method: "tqerp_mrcms.api.create_claim_from_ip",   // your python method
                    args: {
                        ip_no: frm.doc.name
                    },
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.msgprint("Claim Created Successfully!");

                            // Redirect to the new Claim document
                            frappe.set_route("Form", "Claim", r.message);
                        }
                    }
                });

            }, __("Actions"));
        }
    }

});

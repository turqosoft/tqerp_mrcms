frappe.ui.form.on('Insured Person', {

    refresh(frm) {
        frm.set_query("dispensary", () => {
            return {
                filters: { type: "Dispensary" }
            };
        });

        frm.trigger('update_nominee_options');

        // -------------------------------
        // Create Claim Button
        // -------------------------------
        if (!frm.is_new()) {
            frm.add_custom_button('Create Claim', () => {
                frappe.call({
                    method: "tqerp_mrcms.api.create_claim_from_ip",
                    args: { ip_no: frm.doc.name },
                    callback(r) {
                        if (!r.exc) {
                            frappe.msgprint("Claim Created Successfully!");
                            frappe.set_route("Form", "Claim", r.message);
                        }
                    }
                });
            }, __("Actions"));
        }
    },

    // -------------------------------
    // Family table changes
    // -------------------------------
    family_members_add(frm) {
        frm.trigger('update_nominee_options');
    },

    family_members_remove(frm) {
        frm.trigger('update_nominee_options');
    },

    update_nominee_options(frm) {

        let options = [''];

        (frm.doc.family_members || []).forEach(row => {
            if (row.member_name) {
                options.push(row.member_name);
            }
        });

        if (frm.fields_dict.nominee_details) {
            frm.fields_dict.nominee_details.grid.update_docfield_property(
                'name_of_nominee',
                'options',
                options.join('\n')
            );

            frm.refresh_field('nominee_details');
        }
    }
});


frappe.ui.form.on('Family Members', {
    member_name(frm) {
        update_nominee_options(frm);
    },
    relation(frm) {
        update_nominee_options(frm);
    },
    dob(frm) {
        update_nominee_options(frm);
    }
});



frappe.ui.form.on('Nominee', {
    name_of_nominee(frm, cdt, cdn) {

        let nominee = locals[cdt][cdn];
        if (!nominee.name_of_nominee) return;

        let member = (frm.doc.family_members || []).find(
            m => m.member_name === nominee.name_of_nominee
        );

        if (member) {
            frappe.model.set_value(cdt, cdn, 'relation_with_ip', member.relation || '');
            frappe.model.set_value(cdt, cdn, 'date_of_birth', member.dob || '');
        }
    }
});




function update_nominee_options(frm) {

    let options = [];

    (frm.doc.family_members || []).forEach(row => {
        if (row.member_name) {
            options.push(row.member_name); // ✅ STORE DISPLAY NAME
        }
    });

    if (frm.fields_dict.nominee_details) {
        let field = frm.fields_dict.nominee_details.grid
            .get_field('name_of_nominee');

        field.df.options = options.join('\n');
        frm.fields_dict.nominee_details.grid.refresh();
    }
}

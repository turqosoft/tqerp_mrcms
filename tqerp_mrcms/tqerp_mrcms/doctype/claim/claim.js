// ------------------------------
// Helper function to fetch family members
// ------------------------------
function fetch_family_members(frm) {
    if (!frm.doc.ip_no) return;

    frappe.call({
        method: "tqerp_mrcms.api.get_family_members_for_dropdown",
        args: { ip_no: frm.doc.ip_no },
        callback(r) {
            if (r.message) {
                let options = r.message.join("\n"); // convert array to newline-separated string
                frm.set_df_property("name_of_patient", "options", options);
                frm.refresh_field("name_of_patient");

                // If only one member, auto-select and trigger auto-fill
                if (r.message.length === 1) {
                    frm.set_value("name_of_patient", r.message[0]);
                    frm.events.name_of_patient(frm);
                }
            }
        },
        error(err) {
            console.error("Error fetching family members:", err);
        }
    });
}

// ------------------------------
// Helper function to fetch IP details and bank details
// ------------------------------
function fetch_ip_details(frm) {
    if (!frm.doc.ip_no) return;

    frappe.call({
        method: "frappe.client.get",
        args: {
            doctype: "Insured Person",
            name: frm.doc.ip_no
        },
        callback(r) {
            if (r.message) {
                const ip = r.message;

                // Auto-fill IP details
                frm.set_value("ip_name", ip.ip_name || "");
                frm.set_value("phone", ip.phone || "");
                frm.set_value("dispensary", ip.dispensary || "");

                // Auto-fill first bank account if exists
                const banks = ip.bank_accounts || [];
                if (banks.length > 0) {
                    const bank = banks[0]; // pick first bank account
                    frm.set_value("bank_name", bank.bank || "");
                    frm.set_value("bank_account_no", bank.acc_no || "");
                    frm.set_value("branch", bank.branch || "");
                    frm.set_value("ifs_code", bank.ifsc_code || "");
                } else {
                    frm.set_value("bank_name", "");
                    frm.set_value("bank_account_no", "");
                    frm.set_value("branch", "");
                    frm.set_value("ifs_code", "");
                }
            }
        },
        error(err) {
            console.error("Error fetching IP details:", err);
        }
    });
}

// ------------------------------
// Main client script
// ------------------------------
frappe.ui.form.on('Claim', {

    refresh(frm) {
        // IP dropdown
        frm.set_query("ip_no", () => ({ query: "tqerp_mrcms.api.get_ip_details_list" }));

        // name_of_patient options set dynamically in ip_no trigger
        frm.set_query("name_of_patient", () => ({}));
    },

    onload(frm) {
        // Load Default Checklist if empty
        if (!frm.doc.claim_templates) load_claim_checklist(frm, true);

        // Make checklist fields readonly after a short delay
        setTimeout(() => make_claim_checklist_readonly(frm), 500);

        // Route options support
        const opts = frappe.route_options || {};
        if (opts.ip_no) frm.set_value("ip_no", opts.ip_no);
        if (opts.ip_name) frm.set_value("ip_name", opts.ip_name);

        // Ensure patient field is editable
        frm.set_df_property("name_of_patient", "read_only", 0);

        // If IP already set, fetch family members & IP details
        if (frm.doc.ip_no) {
            fetch_family_members(frm);
            fetch_ip_details(frm);
        }
    },

    ip_no(frm) {
        // Reset patient & IP details
        frm.set_value("name_of_patient", "");
        frm.set_value("relation", "");
        frm.set_value("age_of_patient", "");
        frm.set_value("bank_name", "");
        frm.set_value("bank_account_no", "");
        frm.set_value("branch", "");
        frm.set_value("ifs_code", "");
        frm.set_value("ip_name", "");
        frm.set_value("phone", "");

        // Fetch family members and IP details for selected IP
        if (frm.doc.ip_no) {
            fetch_family_members(frm);
            fetch_ip_details(frm);
        }
    },

    name_of_patient(frm) {
        if (!frm.doc.ip_no || !frm.doc.name_of_patient) return;

        frappe.call({
            method: "tqerp_mrcms.api.get_family_member_details",
            args: {
                ip_no: frm.doc.ip_no,
                member_name: frm.doc.name_of_patient
            },
            callback(r) {
                if (!r.message) {
                    frm.set_value("relation", "");
                    frm.set_value("age_of_patient", "");
                    return;
                }

                frm.set_value("relation", r.message.relation || "");

                // Calculate age from dob if available
                if (r.message.dob) {
                    const dob = new Date(r.message.dob);
                    const today = new Date();
                    let age = today.getFullYear() - dob.getFullYear();
                    const m = today.getMonth() - dob.getMonth();
                    if (m < 0 || (m === 0 && today.getDate() < dob.getDate())) {
                        age--;
                    }
                    frm.set_value("age_of_patient", age);
                } else if (r.message.age_of_patient) {
                    frm.set_value("age_of_patient", r.message.age_of_patient);
                } else {
                    frm.set_value("age_of_patient", "");
                }
            },
            error(err) {
                console.error("Error fetching family member details:", err);
            }
        });
    },

    claim_objection_template(frm) { load_claim_objections(frm); },
    claim_templates(frm) { load_claim_checklist(frm); }

});

// ------------------------------
// Load Claim Objections
// ------------------------------
function load_claim_objections(frm) {
    if (!frm.doc.claim_objection_template) {
        frm.clear_table('claim_objection_details');
        frm.refresh_field('claim_objection_details');
        return;
    }

    frappe.db.get_doc('Claim Objections', frm.doc.claim_objection_template)
        .then(doc => {
            frm.clear_table('claim_objection_details');
            (doc.objection || []).forEach(row => {
                let child = frm.add_child('claim_objection_details');
                child.claim_objection = row.objection || "";
            });
            frm.refresh_field('claim_objection_details');
        });
}

// ------------------------------
// Load Claim Checklist
// ------------------------------
function load_claim_checklist(frm, use_default = false) {
    let template = frm.doc.claim_templates;

    if (!template && use_default) {
        frappe.db.get_single_value('MRCMS Settings', 'default_claim_checklist')
            .then(default_template => {
                if (default_template) {
                    frm.set_value('claim_templates', default_template);
                    frappe.db.get_doc('Claim Checklist', default_template)
                        .then(doc => populate_claim_checklist(frm, doc));
                }
            });
        return;
    }

    if (template) {
        frappe.db.get_doc('Claim Checklist', template)
            .then(doc => populate_claim_checklist(frm, doc));
        return;
    }

    frm.clear_table('claim_checklist');
    frm.refresh_field('claim_checklist');
}

// ------------------------------
// Populate Checklist
// ------------------------------
function populate_claim_checklist(frm, doc) {
    frm.clear_table('claim_checklist');
    (doc.claim_checklist_details || []).forEach(row => {
        let child = frm.add_child('claim_checklist');
        child.criteria = row.criteria || "";
        child.required = row.required || 0;
        child.present = row.present || 0;
    });
    frm.refresh_field('claim_checklist');

    setTimeout(() => make_claim_checklist_readonly(frm), 300);
}

// ------------------------------
// Safe Readonly Mode
// ------------------------------
function make_claim_checklist_readonly(frm) {
    let field = frm.get_field('claim_checklist');
    if (!field || !field.grid) return;

    let grid = field.grid;
    if (!grid.grid_rows || grid.grid_rows.length === 0) return;

    grid.grid_rows.forEach(row => {
        if (row.fields_dict?.criteria) row.fields_dict.criteria.df.read_only = 1;
        if (row.fields_dict?.required) row.fields_dict.required.df.read_only = 1;
        if (row.fields_dict?.present) row.fields_dict.present.df.read_only = 0;
    });

    grid.cannot_add_rows = true;
    grid.cannot_delete_rows = true;

    frm.refresh_field('claim_checklist');

    setTimeout(() => {
        try {
            $(grid.wrapper).find('.grid-add-row, .grid-footer, .grid-empty').hide();
        } catch (e) {
            console.error("Error hiding grid elements:", e);
        }
    }, 200);
}

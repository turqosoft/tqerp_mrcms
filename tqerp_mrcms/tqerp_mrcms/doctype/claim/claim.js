// ------------------------------
// Main client script
// ------------------------------
frappe.ui.form.on('Claim', {

    refresh(frm) {
        frm.set_query("ip_no", () => ({ query: "tqerp_mrcms.api.get_ip_details_list" }));
        frm.set_query("name_of_patient", () => ({}));
        // Remember current value on load/refresh
        frm._last_passed_amount = frm.doc.passed_amount;
    },

    validate(frm) {
        if (frm.doc.type === 'IP' && !frm.doc.hospital) {
            frappe.msgprint(__('Hospital is mandatory when Type is IP.'));
            frappe.validated = false;
        }
        if (frm.doc.type === 'IP' && !frm.doc.in_patient_no) {
            frappe.msgprint(__('In Patient Number is mandatory when Type is IP.'));
            frappe.validated = false;
        }
        if (frm.doc.claim_status === 'Sanctioned' && !frm.doc.passed_amount) {
            frappe.msgprint(__('Passed Amount is mandatory.'));
            frappe.validated = false;
        }
    },

    onload(frm) {
        frm.set_df_property("name_of_patient", "read_only", 0);

        if (frm.doc.workflow_state !== 'IMO Review') {
            frm.set_df_property("passed_amount", "read_only", 1);
            frm.set_df_property("rupees", "read_only", 1);
        } else {
            frm.set_df_property('passed_amount', 'read_only', 0);
            frm.set_df_property('rupees', 'read_only', 0);
        }

        if (frm.doc.ip_no) {
            fetch_family_members(frm);
            fetch_ip_details(frm);
        }

        if (!frm.doc.claim_templates) load_claim_checklist(frm, true);

        setTimeout(() => make_claim_checklist_readonly(frm), 500);

        const opts = frappe.route_options || {};
        if (opts.ip_no) frm.set_value("ip_no", opts.ip_no);
        if (opts.ip_name) frm.set_value("ip_name", opts.ip_name);
    },

    ip_no(frm) {
        [
            "name_of_patient", "relation", "age_of_patient",
            "bank_name", "bank_account_no", "branch", "ifs_code",
            "ip_name", "phone"
        ].forEach(f => frm.set_value(f, ""));

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
                    if (frm.doc.relation) frm.set_value("relation", "");
                    if (frm.doc.age_of_patient) frm.set_value("age_of_patient", "");
                    return;
                }

                // Set only if value is actually different to avoid overwriting user edits
                if (frm.doc.relation !== r.message.relation) {
                    frm.set_value("relation", r.message.relation);
                }
                if (frm.doc.age_of_patient !== r.message.age_of_patient) {
                    frm.set_value("age_of_patient", r.message.age_of_patient);
                }

            }
        });
    },

    claim_objection_template(frm) { load_claim_objections(frm); },
    claim_templates(frm) { load_claim_checklist(frm); },

    before_save(frm) {
        const field = frm.get_field("name_of_patient");
        let options = field.df.options ? field.df.options.split("\n") : [];
        const value = frm.doc.name_of_patient;

        if (value && !options.includes(value)) {
            options.push(value);
            frm.set_df_property("name_of_patient", "options", options.join("\n"));
        }
    },
    passed_amount(frm) {
        console.log("Passed Amount event fired:", frm.doc.passed_amount);

        // 1) Do nothing for already finalised claims
        if (["Sanctioned", "Paid", "Closed"].includes(frm.doc.claim_status)) {
            console.log("Claim is final status, skipping passed_amount logic.");
            return;
        }

        // 2) Ignore auto-trigger on form load / unchanged value
        if (frm._last_passed_amount === frm.doc.passed_amount) {
            console.log("passed_amount unchanged from last value, skipping.");
            return;
        }

        // Update last value only when we decide this is a real change
        frm._last_passed_amount = frm.doc.passed_amount;

        const val = Number(frm.doc.passed_amount || 0);
        console.log("Passed Amount (number):", val);

        // 3) If zero/empty → clear and exit
        if (!val || val === 0) {
            if (frm.doc.rupees) frm.set_value("rupees", "");
            if (frm.doc.claim_category) frm.set_value("claim_category", "");
            return;
        }


        if (!frm.doc.passed_amount || frm.doc.passed_amount == 0) {
            frm.set_value("rupees", "");
            frm.set_value("claim_category", "");
            return;
        }

        // 4) Number → words call
        frappe.call({
            method: "tqerp_mrcms.api.number_to_words_indian",
            args: {
                num: val
            },
            callback: function (r) {
                console.log("API Response (Words):", r.message);

                if (r.message) {
                    const currentWords = String(frm.doc.rupees || "");
                    const newWords = String(r.message || "");
                    if (currentWords !== newWords) {
                        frm.set_value("rupees", r.message);
                    }
                } else {
                    frappe.msgprint("Number to words returned empty!");
                }
            },
            error: function (err) {
                console.error("API Error (Words):", err);
                frappe.msgprint("Number to words conversion failed.");
            }
        });


        // 5) Category call
        frappe.call({
            method: "tqerp_mrcms.api.get_claim_category_by_amount",
            args: {
                passed_amount: val
            },
            callback: function (r) {
                console.log("API Response (Category):", r.message);

                if (r.message) {
                    const currentCat = String(frm.doc.claim_category || "");
                    const newCat = String(r.message || "");
                    if (currentCat !== newCat) {
                        frm.set_value("claim_category", r.message);
                        frappe.show_alert({
                            message: __("Category auto-selected: " + r.message),
                            indicator: "green"
                        });
                    }
                } else {
                    if (frm.doc.claim_category) {
                        frm.set_value("claim_category", "");
                    }
                    frappe.msgprint("No Claim Category found for this amount.");
                }
            },
            error: function (err) {
                console.error("API Error (Category):", err);
            }
        });
    },
    // ------------------------------
    // CLAIM STATUS PROGRESS LOGGER
    // ------------------------------
    claim_status(frm) {
        if (!frm.doc.claim_status) return;

        const rows = frm.doc.claim_process || [];
        const last_row = rows.length ? rows[rows.length - 1] : null;

        if (last_row && last_row.activity === `Claim status changed to "${frm.doc.claim_status}"`) {
            console.log("Duplicate status change ignored.");
            return;
        }

        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "User",
                filters: { name: frappe.session.user },
                fieldname: "office"
            },
            callback(r) {
                let office = r.message?.office || "Not Set";

                frm.add_child("claim_process", {
                    user: frappe.session.user,
                    activity: `Claim status changed to "${frm.doc.claim_status}"`,
                    office: office,
                    date: frappe.datetime.now_datetime()
                });

                frm.refresh_field("claim_process");

                frappe.show_alert({
                    message: "Claim progress updated",
                    indicator: "green"
                });
            }
        });
    }
});


// ------------------------------
// Helper function to fetch family members
// ------------------------------
function fetch_family_members(frm) {
    if (!frm.doc.ip_no) return;

    frappe.call({
        method: "tqerp_mrcms.api.get_family_members_for_dropdown",
        args: { ip_no: frm.doc.ip_no },
        callback(r) {
            let options = [];
            if (r.message && r.message.length) {
                options = r.message;
            }

            // Include currently typed value to prevent loss
            const current_value = frm.doc.name_of_patient;
            if (current_value && !options.includes(current_value)) {
                options.push(current_value);
            }

            // Set options as newline-separated string for Select field
            frm.set_df_property("name_of_patient", "options", options.join("\n"));
            frm.refresh_field("name_of_patient");

            // Auto-select if only one member
            if (r.message && r.message.length === 1) {
                frm.set_value("name_of_patient", r.message[0]);
                frm.events.name_of_patient(frm);
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

                frm.set_value("ip_name", ip.ip_name || "");
                frm.set_value("phone", ip.phone || "");
                frm.set_value("dispensary", ip.dispensary || "");
                frm.set_value("address", ip.address || "");

                const banks = ip.bank_accounts || [];
                if (banks.length > 0) {
                    const bank = banks[0];
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
    const field = frm.get_field('claim_checklist');
    if (!field || !field.grid) return;

    const grid = field.grid;
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
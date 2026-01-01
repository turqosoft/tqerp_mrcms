// ------------------------------
// Main client script
// ------------------------------
frappe.ui.form.on('Claim', {

    refresh(frm) {
        frm.set_query("ip_no", () => ({ query: "tqerp_mrcms.api.get_ip_details_list" }));
        frm.set_query("name_of_patient", () => ({}));
        // Remember current value on load/refresh
        frm._last_passed_amount = frm.doc.passed_amount;
        // make custom remakrs field read-only so that previous remarks should not be edited.
        apply_readonly_to_comments(frm);

        // Claim Management
        // toggle_claim_rate_tables(frm);

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
            frm.set_df_property("package_rate", "read_only", 1);
            frm.set_df_property("non_package_rate", "read_only", 1);

        } else {
            frm.set_df_property('passed_amount', 'read_only', 0);
            frm.set_df_property('rupees', 'read_only', 0);
            frm.set_df_property("package_rate", "read_only", 0);
            frm.set_df_property("non_package_rate", "read_only", 0);
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

        // make custom remakrs field read-only so that previous remarks should not be edited.
        apply_readonly_to_comments(frm);
        frm.set_df_property('organisation_code', 'read_only', 1);
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
    dispensary: function (frm) {
        if (frm.doc.dispensary) {
            frappe.db.get_value('Organisation', frm.doc.dispensary, 'organisation_code')
                .then(r => {
                    if (r.message) {
                        frm.set_value('organisation_code', r.message.organisation_code);
                    }
                });
        } else {
            frm.set_value('organisation_code', '');
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

        // 1) Do nothing for already finalised claims
        if (["Sanctioned", "Paid", "Closed"].includes(frm.doc.claim_status)) {
            return;
        }

        // 2) Ignore auto-trigger on form load / unchanged value
        if (frm._last_passed_amount === frm.doc.passed_amount) {
            return;
        }

        // Update last value only when we decide this is a real change
        frm._last_passed_amount = frm.doc.passed_amount;

        const val = Number(frm.doc.passed_amount || 0);

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
    // ------------------------------
    // CLAIM STATUS PROGRESS LOGGER
    // ------------------------------
    claim_status(frm) {
        if (!frm.doc.claim_status) return;

        const rows = frm.doc.claim_process || [];
        const last_row = rows.length ? rows[rows.length - 1] : null;

        if (last_row && last_row.activity === `Claim status changed to "${frm.doc.claim_status}"`) {
            return;
        }

        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "User",
                filters: { name: frappe.session.user },
                fieldname: "organisation"
            },
            callback(r) {
                let organisation = r.message?.organisation || "Not Set";

                frm.add_child("claim_process", {
                    user: frappe.session.user,
                    activity: `Claim status changed to "${frm.doc.claim_status}"`,
                    organisation: organisation,
                    date: frappe.datetime.now_datetime()
                });

                frm.refresh_field("claim_process");

                frappe.show_alert({
                    message: "Claim progress updated",
                    indicator: "green"
                });
            }
        });
    },
    amount_claimed(frm) {
        if (!frm.doc.amount_claimed) return;

        frappe.call({
            method: "tqerp_mrcms.tqerp_mrcms.doctype.claim.claim.get_required_documents",
            args: {
                amount_claimed: frm.doc.amount_claimed
            },
            callback(r) {
                if (!r.message) return;
                frm.set_value("claim_category", r.message.claim_category);
                frm.clear_table("claim_required_documents");

                r.message.documents.forEach(d => {
                    let row = frm.add_child("claim_required_documents");
                    row.claim_doc_master = d.claim_doc_master;
                    row.mandatory = d.mandatory;
                });

                frm.refresh_field("claim_required_documents");
            }
        });
    },
    claim_remarks_add(frm, cdt, cdn) {
        const row = locals[cdt][cdn];

        frappe.model.set_value(cdt, cdn, "comment_by", frappe.session.user);
        frappe.model.set_value(cdt, cdn, "claim_status", frm.doc.claim_status);
        frappe.model.set_value(cdt, cdn, "date", frappe.datetime.now_datetime());

        frappe.call({
            method: "frappe.db.get_value",
            args: {
                doctype: "User",
                filters: { name: frappe.session.user },
                fieldname: ["full_name", "authority"]
            },
            callback: function (r) {
                if (r.message) {
                    frappe.model.set_value(
                        cdt,
                        cdn,
                        "comment_by_full_name",
                        r.message.full_name || frappe.session.user
                    );
                    frappe.model.set_value(
                        cdt,
                        cdn,
                        "comment_by_authority",
                        r.message.authority || ""
                    );
                }
            }
        });

        apply_readonly_to_comments(frm);
    },

    claim_remarks_comment(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.comment_by !== frappe.session.user || row.is_locked) {
            frappe.msgprint("You cannot edit remarks by other users or locked remarks.");
            frm.refresh_field("claim_remarks");
        }
    },
    // RATE MANAGEMENT
    // package_rate(frm) {
    //     toggle_claim_rate_tables(frm);
    //     // populate_rate_item_fields(frm, 'Package');
    // },
    // non_package_rate(frm) {
    //     toggle_claim_rate_tables(frm);
    //     // populate_rate_item_fields(frm, 'Non-Package');
    // },
    setup(frm) {
        frm.fields_dict['package_rate_items'].grid.get_field('rate_item_name').get_query = function () {
            return {
                query: "tqerp_mrcms.api.rate_item_link_query",
                filters: {
                    item_type: "Package",
                    is_active: 1
                }
            };
        };
        frm.fields_dict['non_package_rate_items'].grid.get_field('rate_item_name').get_query = function () {
            return {
                query: "tqerp_mrcms.api.rate_item_link_query",
                filters: {
                    item_type: "Non-Package",
                    is_active: 1
                }
            };
        };
    },
    // RATE MANAGEMENT ENDS HERE
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

// Helper function to make comments read-only for others
function apply_readonly_to_comments(frm) {
    const grid = frm.fields_dict.claim_remarks.grid;

    //     grid.grid_rows.forEach(row => {
    //         const doc = locals['Claim Remarks'][row.docname];

    //         if (doc.comment_by !== frappe.session.user || doc.is_locked) {
    //             row.toggle_enable('comment', false);
    //         } else {
    //             row.toggle_enable('comment', true);
    //         }
    //     });
}

frappe.ui.form.on('Claim Required Documents', {

    // Trigger when document master is selected
    claim_doc_master: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.claim_doc_master) return;

        frappe.db.get_list('Claim Document Rule Details', {
            filters: { claim_doc_master: row.claim_doc_master },
            fields: ['mandatory'],
            limit_page_length: 1
        }).then(rule_details => {
            if (rule_details && rule_details.length) {
                frappe.model.set_value(
                    cdt,
                    cdn,
                    'mandatory',
                    rule_details[0].mandatory
                );
                frm.refresh_field('claim_required_documents');
            }
        });
    },

    // Trigger when file is uploaded
    uploaded_file: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.uploaded_file || !row.claim_doc_master) return;

        // ---- GET SETTINGS (FILE SIZE) ----
        frappe.db.get_doc('Mrcms Settings', 'Mrcms Settings').then(settings => {
            let max_size = settings.upload_file_size || 0;
            let unit = settings.upload_file_size_unit || 'MB';

            let max_bytes = unit === 'KB'
                ? max_size * 1024
                : max_size * 1024 * 1024;

            // ---- GET FILE INFO ----
            frappe.db.get_value(
                'File',
                { file_url: row.uploaded_file },
                ['file_size', 'file_name']
            ).then(r => {
                if (!r || !r.message) return;

                let file_size = r.message.file_size || 0;
                let filename = r.message.file_name;
                let ext = filename.split('.').pop().toLowerCase();

                // ---- GET DOCUMENT MASTER ----
                frappe.db.get_doc('Claim Document Master', row.claim_doc_master)
                    .then(doc_master => {

                        // ---- EXTENSION CHECK ----
                        let allowed_extensions = [];
                        if (doc_master.file_type_jpg) allowed_extensions.push('jpg');
                        if (doc_master.file_type_jpeg) allowed_extensions.push('jpeg');
                        if (doc_master.file_type_png) allowed_extensions.push('png');
                        if (doc_master.file_type_gif) allowed_extensions.push('gif');
                        if (doc_master.file_type_pdf) allowed_extensions.push('pdf');

                        if (!allowed_extensions.includes(ext)) {
                            frappe.msgprint({
                                title: 'Invalid File Type',
                                indicator: 'red',
                                message: 'Allowed types: jpg, jpeg, png, gif, pdf'
                            });
                            frappe.model.set_value(cdt, cdn, 'uploaded_file', null);
                            return;
                        }

                        // ---- FILE SIZE CHECK (ADDED) ----
                        if (file_size > max_bytes) {
                            frappe.msgprint({
                                title: 'File Size Exceeded',
                                indicator: 'red',
                                message: `Maximum allowed size is ${max_size} ${unit}`
                            });
                            frappe.model.set_value(cdt, cdn, 'uploaded_file', null);
                            return;
                        }

                        // ---- SET META FIELDS ----
                        frappe.model.set_value(
                            cdt,
                            cdn,
                            'uploaded_on',
                            frappe.datetime.now_datetime()
                        );
                        frappe.model.set_value(
                            cdt,
                            cdn,
                            'uploaded_by',
                            frappe.session.user
                        );

                        frm.refresh_field('claim_required_documents');
                    });
            });
        });
    }
});

// RATE MANAGEMENT
function toggle_claim_rate_tables(frm) {
    frm.toggle_display('package_rate_items', frm.doc.package_rate);
    frm.toggle_display('non_package_rate_items', frm.doc.non_package_rate);
}

function populate_rate_item_fields(cdt, cdn) {
    const row = locals[cdt][cdn];
    if (!row.rate_item_name) return;

    //  Item Code
    frappe.model.set_value(cdt, cdn, "item_code", row.rate_item_name);

    // Item Name (from Item master)
    frappe.db.get_value("Item", row.rate_item_name, "item_name")
        .then(r => {
            if (r && r.message) {
                frappe.model.set_value(cdt, cdn,
                    "item_name",
                    r.message.item_name
                );
            }
        });

    // Rate (from Item Rate)
    frappe.call({
        method: "tqerp_mrcms.api.get_latest_rate_for_item",
        args: {
            item_code: row.rate_item_name
        },
        callback(r) {
            if (!r.message) return;
            frappe.model.set_value(cdt, cdn, "rate", r.message.rate);
        }
    });
}

frappe.ui.form.on('Package Rate Item', {
    rate_item_name(frm, cdt, cdn) {
        populate_rate_item_fields(cdt, cdn, frm);
    },
    rate: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        calculate_row_total(row);
        calculate_table_totals(frm);
        calculate_passed_amount(frm);
        frm.refresh_field('package_rate_items');
    },
    qty: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        calculate_row_total(row);
        calculate_table_totals(frm);
        calculate_passed_amount(frm);
        frm.refresh_field('package_rate_items');
    },
    admissible_percentage: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        calculate_row_total(row);
        calculate_table_totals(frm);
        calculate_passed_amount(frm);
        frm.refresh_field('package_rate_items');
    }
});

frappe.ui.form.on('Non Package Rate Item', {
    rate_item_name(frm, cdt, cdn) {
        populate_rate_item_fields(cdt, cdn);
    },
    rate: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        calculate_row_total(row);
        calculate_table_totals(frm);
        calculate_passed_amount(frm);
        frm.refresh_field('non_package_rate_items');
    },
    qty: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        calculate_row_total(row);
        calculate_table_totals(frm);
        calculate_passed_amount(frm);
        frm.refresh_field('non_package_rate_items');
    },
    admissible_percentage: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        calculate_row_total(row);
        calculate_table_totals(frm);
        calculate_passed_amount(frm);
        frm.refresh_field('non_package_rate_items');
    }
});

// Utility functions
function calculate_row_total(row) {
    let rate = row.rate || 0;
    let qty = row.qty || 1;
    let perc = row.admissible_percentage || 100;
    row.total = (rate * qty * perc / 100);
}

function calculate_passed_amount(frm) {
    let total = 0;
    if(frm.doc.package_rate) {
        (frm.doc.package_rate_items || []).forEach(row => total += row.total || 0);
    }
    if(frm.doc.non_package_rate) {
        (frm.doc.non_package_rate_items || []).forEach(row => total += row.total || 0);
    }
    frm.set_value("passed_amount", total);
}

// Calculate table totals and overall passed_amount
function calculate_table_totals(frm) {
    let package_total = 0;
    let non_package_total = 0;

    // Only calculate package total if package_rate is selected
    if (frm.doc.package_rate) {
        (frm.doc.package_rate_items || []).forEach(row => package_total += row.total || 0);
        frm.set_value("total_package_rate", package_total);
    } else {
        frm.set_value("total_package_rate", null);
    }

    // Only calculate non-package total if non_package_rate is selected
    if (frm.doc.non_package_rate) {
        (frm.doc.non_package_rate_items || []).forEach(row => non_package_total += row.total || 0);
        frm.set_value("total_non_package_rate", non_package_total);
    } else {
        frm.set_value("total_non_package_rate", null);
    }

    // Update overall passed_amount using only selected rates
    let passed_amount = (frm.doc.package_rate ? package_total : 0) +
        (frm.doc.non_package_rate ? non_package_total : 0);
    frm.set_value("passed_amount", passed_amount);
}
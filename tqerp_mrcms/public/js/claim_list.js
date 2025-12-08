// -----------------------------------------------------
// Recursive function to get all child offices
// -----------------------------------------------------
async function getChildOfficesRecursive(parent_office) {
    let children = await frappe.db.get_list("Office", {
        fields: ["name", "is_group"],
        filters: { parent_office: parent_office }
    });

    let result = [];
    for (let child of children) {
        result.push(child.name);

        if (child.is_group) {
            let sub_children = await getChildOfficesRecursive(child.name);
            result = result.concat(sub_children);
        }
    }
    return result;
}



// -----------------------------------------------------
// Claim ListView Settings
// -----------------------------------------------------
frappe.listview_settings['Claim'] = {
    order_by: 'claim_date desc',

    onload: async function (listview) {
        try {

            // -----------------------------------------------------
            //  Create ALLOCATION, SUM, DIFFERENCE Boxes
            // -----------------------------------------------------
            setTimeout(() => {
                if (listview.doctype !== "Claim") return;
                if (!document.getElementById("allocation_main_box")) {
                    const html = `
                        <div id="allocation_main_box" style="
                            display:flex;
                            align-items:center;
                            gap:20px;
                            margin-left:12px;
                        ">

                            <!-- Allocation box (always visible) -->
                            <div style="display:flex; align-items:center; gap:6px;">
                                <label style="font-size:13px;">Allocation:</label>
                                <input type="number" id="allocation_input"
                                    style="width:120px; padding:4px 6px;
                                    font-size:13px; border:1px solid #ccc;
                                    border-radius:4px;" />
                            </div>

                            <!-- Sum box (visible when selected) -->
                            <div id="sum_box" style="display:none; align-items:center; gap:6px;">
                                <label style="font-size:13px;">Sum:</label>
                                <input type="text" id="sum_input"
                                    style="width:120px; padding:4px 6px;
                                    font-size:13px; border:1px solid #ccc;
                                    border-radius:4px;" readonly />
                            </div>

                            <!-- Difference box -->
                            <div id="diff_box" style="display:none; align-items:center; gap:6px;">
                                <label style="font-size:13px;">Difference:</label>
                                <input type="text" id="diff_input"
                                    style="width:120px; padding:4px 6px;
                                    font-size:13px; border:1px solid #ccc;
                                    border-radius:4px;" readonly />
                            </div>

                        </div>
                    `;

                    $(".page-actions").prepend(html);
                    console.log("Allocation, Sum, Difference boxes added");

                    bind_sum_diff_handler(listview);
                }
            }, 600);



            // -----------------------------------------------------
            //  Office Based Filter
            // -----------------------------------------------------
            // let user_res = await frappe.db.get_value("User", frappe.session.user, "office");
            // let user_office = user_res?.message?.office;

            // if (!user_office) return;

            // let child_offices = await getChildOfficesRecursive(user_office);
            // let allowed_offices = [user_office, ...child_offices];

            // let ips = await frappe.db.get_list("Insured Person", {
            //     fields: ["name"],
            //     filters: [["local_office", "in", allowed_offices]],
            //     limit: 0
            // });

            // let allowed_ips = ips.map(ip => ip.name);

            // listview.filter_area.add([
            //     ["Claim", "ip_no", "in", allowed_ips]
            // ]);



            // -----------------------------------------------------
            //  Add Action Button — Create Claim Proceedings
            // -----------------------------------------------------
            listview.page.add_action_item(__('Claim Proceedings'), async function () {

                let selected_docs = listview.get_checked_items();
                if (!selected_docs.length) {
                    frappe.msgprint(__('Please select at least one claim.'));
                    return;
                }

                let sanctioned_claims = [];

                for (let doc of selected_docs) {
                    let full_doc = await frappe.db.get_doc('Claim', doc.name);

                    if (full_doc.claim_status === "Sanctioned") {
                        sanctioned_claims.push({
                            claim_no: full_doc.claim_no || full_doc.name,
                            claim_date: full_doc.claim_date || "",
                            ip_name: full_doc.ip_name || "",
                            ip_no: full_doc.ip_no || "",
                            phone: full_doc.phone || "",
                            ifs_code: full_doc.ifs_code || "",
                            bank_account_no: full_doc.bank_account_no || "",
                            passed_amount: full_doc.passed_amount || 0
                        });
                    }
                }

                if (!sanctioned_claims.length) {
                    frappe.msgprint(__('No selected claims are sanctioned.'));
                    return;
                }

                try {
                    let r = await frappe.call({
                        method: "tqerp_mrcms.api.create_claim_proceeding_for_multiple",
                        args: { claims_data: JSON.stringify(sanctioned_claims) }
                    });

                    if (r.message?.name) {
                        frappe.set_route("Form", "Claim Proceedings", r.message.name);
                        frappe.msgprint(__('Claim Proceedings created.'));
                    }

                } catch (err) {
                    frappe.msgprint(__('Error: {0}', [err.message]));
                }
            });


            // -----------------------------------------------------
            //  Add Action Button — Claim Bundle Management
            // -----------------------------------------------------
            listview.page.add_action_item(__('Claim Bundle Management'), async function () {
 
                let selected_docs = listview.get_checked_items();
                if (!selected_docs.length) {
                    frappe.msgprint(__('Please select at least one claim.'));
                    return;
                }
           
                let sanctioned_claims = [];
           
                for (let doc of selected_docs) {
                    let full_doc = await frappe.db.get_doc('Claim', doc.name);
           
                    if (full_doc.claim_status === "Sanctioned") {
                        sanctioned_claims.push({
                            claim_no: full_doc.name,                            
                            claim_date: full_doc.claim_date || "",
                            ip_name: full_doc.ip_name || "",
                            ip_no: full_doc.ip_no || "",
                            name_of_patient: full_doc.name_of_patient || "",
                            dispensary: full_doc.dispensary || "",
                            claim_status: full_doc.claim_status || "",
                            amount_claimed: full_doc.amount_claimed || 0,
                            passed_amount: full_doc.passed_amount || 0,
                            ifs_code:full_doc.ifs_code || 0,
                            bank_account_no:full_doc.bank_account_no || 0,
                            bank_name:full_doc.bank_name || 0
                           
                        });
                    }
                }
           
                if (!sanctioned_claims.length) {
                    frappe.msgprint(__('No selected claims are sanctioned.'));
                    return;
                }
           
                try {
                    let r = await frappe.call({
                        method: "tqerp_mrcms.api.create_claim_bundle_management",
                        args: { claims_data: JSON.stringify(sanctioned_claims) }
                    });
           
                    if (r.message?.name) {
                        frappe.set_route("Form", "Claim Bundle Management", r.message.name);
                        frappe.msgprint(__('Claim Bundle Management created.'));
                    }
           
                } catch (err) {
                    frappe.msgprint(__('Error: {0}', [err.message]));
                }
            });

        } catch (err) {
            console.error("ListView Load Error:", err);
        }
    }
};




// -----------------------------------------------------
//  SUM + DIFFERENCE HANDLER
// -----------------------------------------------------
function bind_sum_diff_handler(listview) {

    $(document).off("change.claimSumDiff");

    $(document).on("change.claimSumDiff", "input.list-row-checkbox", function () {

        let selected = listview.get_checked_items().map(r => r.name);

        const $sum = $("#sum_box");
        const $diff = $("#diff_box");

        if (!selected.length) {
            $("#sum_input").val("");
            $("#diff_input").val("");
            $sum.hide();
            $diff.hide();
            return;
        }

        $sum.show();
        $diff.show();

        let sum_total = 0;
        let done = 0;

        selected.forEach(docname => {
            frappe.call({
                method: "frappe.client.get",
                args: { doctype: "Claim", name: docname },
                callback(r) {
                    if (r.message) {
                        sum_total += parseFloat(r.message.passed_amount || 0);
                    }
                    done++;

                    if (done === selected.length) {
                        $("#sum_input").val(sum_total.toFixed(2));
                        update_difference();
                    }
                }
            });
        });
    });

    $(document).on("input", "#allocation_input", function () {
        update_difference();
    });
}



// -----------------------------------------------------
// Calculate DIFF = Allocation - Sum
// -----------------------------------------------------
function update_difference() {
    let allocation = parseFloat($("#allocation_input").val() || 0);
    let sum = parseFloat($("#sum_input").val() || 0);

    let diff = allocation - sum;
    $("#diff_input").val(diff.toFixed(2));
}


// --------------

// frappe.listview_settings['Claim'] = {
//     // Default sorting
//     order_by: 'claim_date desc',  // 'desc' for newest first, use 'asc' for oldest first

//     onload: function(listview) {
//         listview.page.add_action_item(__('Claim Proceedings'), async function() {
//             let selected_docs = listview.get_checked_items();

//             if (!selected_docs.length) {
//                 frappe.msgprint(__('Please select at least one claim.'));
//                 return;
//             }

//             // Filter claims with status "Sanctioned"
//             let sanctioned_claims = [];
//             for (let doc of selected_docs) {
//                 let full_doc = await frappe.db.get_doc('Claim', doc.name);
//                 if (full_doc.claim_status === "Sanctioned") {
//                     sanctioned_claims.push({
//                         claim_no: full_doc.claim_no || full_doc.name || "",
//                         claim_date: full_doc.claim_date || "",
//                         ip_name: full_doc.ip_name || "",
//                         ip_no: full_doc.ip_no || "",
//                         phone: full_doc.phone || "",
//                         ifs_code: full_doc.ifs_code || "",
//                         bank_account_no: full_doc.bank_account_no || "",
//                         passed_amount: full_doc.passed_amount || 0
//                     });
//                 }
//             }

//             if (!sanctioned_claims.length) {
//                 frappe.msgprint(__('No selected claims are sanctioned. Only sanctioned claims can go to proceedings.'));
//                 return;
//             }

//             try {
//                 let r = await frappe.call({
//                     method: "tqerp_mrcms.api.create_claim_proceeding_for_multiple",
//                     args: { claims_data: JSON.stringify(sanctioned_claims) }
//                 });

//                 if (r.message && r.message.name) {
//                     frappe.set_route("Form", "Claim Proceedings", r.message.name);
//                     frappe.msgprint(__('Claim Proceedings created for selected sanctioned claims.'));
//                 } else {
//                     frappe.msgprint(__('Failed to create Claim Proceedings.'));
//                 }
//             } catch (err) {
//                 frappe.msgprint(__('Error creating Claim Proceedings: {0}', [err.message]));
//             }
//         });
//     }
// };


// ---------------

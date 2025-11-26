frappe.ui.form.on('Claim', {
    // Triggered when the form is loaded
    onload: function(frm) {
        const ip_no = frm.doc.ip_no;
        if (!ip_no) return;

        frappe.call({
            method: "tqerp_mrcms.api.get_ip_details",
            args: { ip_no: ip_no },
            callback: function(r) {
                const data = r.message;
                if (!data) return;

                frm.set_value("ip_name", data.ip_name);
                frm.set_value("address", data.address);
                console.log("Address::: "+ data.address);
                frm.set_value("phone", data.phone);
                frm.set_value("employer", data.employer);

                // Calculate age
                if (data.dob) {
                    const dob = new Date(data.dob);
                    const age = Math.floor((Date.now() - dob.getTime()) / (1000 * 60 * 60 * 24 * 365.25));
                    frm.set_value("patient_age", age);
                }

                // Relationship from first family member
                if (data.family_members && data.family_members.length > 0) {
                    frm.set_value("relationship", data.family_members[0].relationship || "");
                }
            }
        });
    },

    // Triggered when ip_no field is changed
    ip_no: function(frm) {
        const ip_no = frm.doc.ip_no;
        if (!ip_no) return;

        frappe.call({
            method: "tqerp_mrcms.api.get_ip_details",
            args: { ip_no: ip_no },
            callback: function(r) {
                const data = r.message;
                if (!data) return;

                frm.set_value("ip_name", data.ip_name);
                frm.set_value("address", data.address);
                frm.set_value("phone", data.phone);
                frm.set_value("employer", data.employer);
            }
        });
    }
});

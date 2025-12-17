// Copyright (c) 2025, Turqosoft Solutions Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Fund Manager", {
	expired(frm) {
        if (frm.doc.expired && !frm.doc.expired_on) {
            frm.set_value("expired_on", frappe.datetime.get_today());
        }
    },
});

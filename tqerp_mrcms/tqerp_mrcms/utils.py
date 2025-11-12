from collections import defaultdict
from json import loads
from typing import TYPE_CHECKING, Optional

import frappe
import frappe.defaults
from frappe import _, qb, throw
from frappe.desk.reportview import build_match_conditions
from frappe.model.meta import get_field_precision
from frappe.query_builder import AliasedQuery, Case, Criterion, Table
from frappe.query_builder.functions import Count, Max, Sum
from frappe.query_builder.utils import DocType
from frappe.utils import (
	add_days,
	cint,
	create_batch,
	cstr,
	flt,
	formatdate,
	get_datetime,
	get_number_format_info,
	getdate,
	now,
	nowdate,
)
from frappe.utils.caching import site_cache
from pypika import Order
from pypika.functions import Coalesce
from pypika.terms import ExistsCriterion

@frappe.whitelist()
def get_authority_children(doctype, parent, company, is_root=False):

	parent_fieldname = "parent_" + frappe.scrub(doctype)
	fields = ["name as value", "is_group as expandable"]
	filters = [["docstatus", "<", 2]]

	filters.append([f'ifnull(`{parent_fieldname}`,"")', "=", "" if is_root else parent])

	if is_root:
		fields += ["root_type", "report_type"] if doctype == "Authority" else []
		filters.append(["company", "=", company])

	else:
		fields += ["root_type", "account_currency"] if doctype == "Authority" else []
		fields += [parent_fieldname + " as parent"]

	acc = frappe.get_list(doctype, fields=fields, filters=filters)


	return acc

@frappe.whitelist()
def add_authority(args=None):
	from frappe.desk.treeview import make_tree_args

	if not args:
		args = frappe.local.form_dict

	args.doctype = "Authority"
	args = make_tree_args(**args)

	ac = frappe.new_doc("Authority")

	if args.get("ignore_permissions"):
		ac.flags.ignore_permissions = True
		args.pop("ignore_permissions")

	ac.update(args)

	if not ac.parent_account:
		ac.parent_account = args.get("parent")

	ac.old_parent = ""
	ac.freeze_account = "No"
	if cint(ac.get("is_root")):
		ac.parent_account = None
		ac.flags.ignore_mandatory = True

	ac.insert()

	return ac.name
app_name = "tqerp_mrcms"
app_title = "Tqerp Mrcms"
app_publisher = "Turqosoft Solutions Pvt. Ltd."
app_description = "MRCMS Application"
app_email = "turqosoft@gmail.com"
app_license = "mit"
# required_apps = []

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/tqerp_mrcms/css/tqerp_mrcms.css"
# app_include_js = "/assets/tqerp_mrcms/js/tqerp_mrcms.js"

# include js, css files in header of web template
# web_include_css = "/assets/tqerp_mrcms/css/tqerp_mrcms.css"
# web_include_js = "/assets/tqerp_mrcms/js/tqerp_mrcms.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "tqerp_mrcms/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
doctype_js = {"Claim" : "public/js/claim.js"}
doctype_list_js = {
    "Claim" : "public/js/claim_list.js",
    "Claim Bundle Management" : "public/js/claim_bundle_management.js",
    "Claim Sanction List":"public/js/claim_sanction_list.js",
    "Claim Payment List":"public/js/claim_payment_list.js"
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "tqerp_mrcms/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "tqerp_mrcms.utils.jinja_methods",
# 	"filters": "tqerp_mrcms.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "tqerp_mrcms.install.before_install"
# after_install = "tqerp_mrcms.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "tqerp_mrcms.uninstall.before_uninstall"
# after_uninstall = "tqerp_mrcms.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "tqerp_mrcms.utils.before_app_install"
# after_app_install = "tqerp_mrcms.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "tqerp_mrcms.utils.before_app_uninstall"
# after_app_uninstall = "tqerp_mrcms.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "tqerp_mrcms.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }

permission_query_conditions = {
	"Claim": "tqerp_mrcms.tqerp_mrcms.doctype.claim.claim.get_permission_query_conditions",
    "Claim Proceedings": "tqerp_mrcms.tqerp_mrcms.doctype.claim_proceedings.claim_proceedings.get_permission_query_conditions",
    "Claim Bundle Management": "tqerp_mrcms.tqerp_mrcms.doctype.claim_bundle_management.claim_bundle_management.get_permission_query_conditions",
    "Claim Sanction List": "tqerp_mrcms.tqerp_mrcms.doctype.claim_sanction_list.claim_sanction_list.get_permission_query_conditions",
    "Claim Payment List": "tqerp_mrcms.tqerp_mrcms.doctype.claim_payment_list.claim_payment_list.get_permission_query_conditions",
}

#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"tqerp_mrcms.tasks.all"
# 	],
# 	"daily": [
# 		"tqerp_mrcms.tasks.daily"
# 	],
# 	"hourly": [
# 		"tqerp_mrcms.tasks.hourly"
# 	],
# 	"weekly": [
# 		"tqerp_mrcms.tasks.weekly"
# 	],
# 	"monthly": [
# 		"tqerp_mrcms.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "tqerp_mrcms.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "tqerp_mrcms.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "tqerp_mrcms.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["tqerp_mrcms.utils.before_request"]
# after_request = ["tqerp_mrcms.utils.after_request"]

# Job Events
# ----------
# before_job = ["tqerp_mrcms.utils.before_job"]
# after_job = ["tqerp_mrcms.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"tqerp_mrcms.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

override_whitelisted_methods = {
    "tqerp_mrcms.www.add_ip_backend.save_ip": "tqerp_mrcms.www.add_ip_backend.save_ip"
}

# Website Route Rules
website_route_rules = [
    {"from_route": "/claims", "to_route": "claim/claim_list"},
    # {"from_route": "/claim/new", "to_route": "claim/add_claim"},
    {"from_route": "/claim/modify", "to_route": "claim/update_claim"},
    {"from_route": "/insured", "to_route": "ip/ip"},
    {"from_route": "/insured/new", "to_route": "ip/add_ip"},
    {"from_route": "/insured/search", "to_route": "ip/select_ip"},
    {"from_route": "/dashboard", "to_route": "dashboard"},
]

# In tqerp_mrcms/hooks.py
# has_website_permission = [
#     "tqerp_mrcms.api.check_page_permission"
# ]
doc_events = {
    "Claim Proceedings": {
        "on_submit": "tqerp_mrcms.api.update_claim_status_on_submit",
        "on_cancel": "tqerp_mrcms.api.update_claim_status_on_cancel"
    }
}

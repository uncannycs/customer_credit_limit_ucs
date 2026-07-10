# -*- coding: utf-8 -*-


# -*- coding: utf-8 -*-
##############################################################################
#
#    ODOO Open Source Management Solution
#
#    ODOO Addon module by Uncanny Consulting Services LLP
#    Copyright (C) 2023 Uncanny Consulting Services LLP (<https://uncannycs.com>).
#
##############################################################################
{
    'name': 'Customer Credit Limit Ucs',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Set customer credit limits with popup warnings and automated manager approval emails',
    'description': """
Customer Credit Limit Approval
==============================
This module implements a rigorous customer credit limit control:
* Adds an 'Active Credit Limit' checkbox in the customer profile (Sales & Purchase tab).
* Displays a 'Credit Limit' amount field dynamically only when credit limit control is activated.
* Enforces validation to prevent saving a credit limit of zero or less when active.
* Automatically blocks sales order confirmation if the credit limit is exceeded.
* Displays a detailed warning popup displaying unpaid invoices and pending sales orders.
* Allows salespeople to request manager approval via a single-click email request.
* Restricts order confirmation to managers only when the credit limit is exceeded.
* Automatically notifies the salesperson via email when the manager approves and confirms the order.
* Logs all request and approval emails directly in the sales order's Chatter.
""",
    "website": "https://uncannycs.com",
    "author": "Uncanny Consulting Services LLP",
    "maintainer": "Uncanny Consulting Services LLP",
    "license": "Other proprietary",
    'depends': ['sale_management', 'account', 'mail', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_templates.xml',
        'wizard/credit_limit_warning_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': True,
    "images": ['static/description/banner.gif'],
    "price": 10,
    "currency": "USD"
}

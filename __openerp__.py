# -*- coding: utf-8 -*-
{
    "name" : "Custom EIS Modifications",
    "version" : "4.17",
    "category" : "Accounting",
    "sequence": 60,
    "complexity" : "normal",
    "author" : "ColourCog.com",
    "website" : "http://colourcog.com",
    "depends" : [
        "base",
        "hr_payroll",
        "hr_payroll_account",
        "hr_payslip_voucher",
        "hr_loan",
        "l10n_bj_payroll",
        "account_accountant",
        "account_check_writing",
        "point_of_sale",
        "purchase",
    ],
    "summary" : "Modifies standard OpenERP functionality",
    "description" : """
Custom EIS Modifications
========================
This module overrides or creates extra functionality for the EIS OpenERP instance.

Extra features:
-------------------------------
* extra balance row in invoice
* extra currency data in invoice
* payments history in invoice
* printable Payment Vouchers
* force cancel button to appear in paid pyslips
* batch validate payslips
* batch cancel payslips
* use current date when duplicating payslip
* batch duplicate payslips with specific target dates
* batch confirm purchase orders
* group payslips by month
* recreate loan workflows
* modified amount-to-text handling to suppress decimals for FCFA
* modified amount-to-text to use absolute numbers (useful for negative payments)
* additional partner mobile number
* additional partner email and mail sending to all partner emails
* use purchase validation date as invoice date
* validate and pay invoices cash using invoice date
* create a read-only accounting group
* create a limited POS group (with read-only rights to accounting)
* create a limited sale group (with read-only rights to accounting)
* batch switch invoice date to purchase order date
* batch validate/pay invoices using the cash method
* batch switch move line period to effective date period
* batch cancel journal entries
* batch shift invoice expense account
* import invoice to setup loan
* switch partner automatically on loan import from invoice
* force invoices to update their status when paid
* import voucher as loan give-out
    """,
    "data" : [
        "security/ir_rule.xml",
        "security/ir.model.access.csv",
        "account_invoice_view.xml",
        "hr_payroll_view.xml",
        "hr_payroll_data.xml",
        "hr_loan_view.xml",
        "hr_loan_data.xml",
        "accounting_data.xml",
        "account_voucher_view.xml",
        "custom_account_report.xml",
        "partner_view.xml",
        "purchase_data.xml",
        "account_invoice_data.xml",
        "account_move_data.xml",
        "account_move_line_data.xml",
    ],
    "application": False,
    "installable": True
}


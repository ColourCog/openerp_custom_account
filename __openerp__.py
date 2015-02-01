{
    "name" : "Custom Account Invoices",
    "version" : "1.1", 
    "category" : "Accounting", 
    "sequence": 60,
    "complexity" : "normal", 
    "author" : "ColourCog.com", 
    "website" : "http://colourcog.com", 
    "depends" : [
        "base", 
        "hr_payroll",
        "account_accountant",
        "account_check_writing",
    ], 
    "summary" : "Modifies the standard invoice reports", 
    "description" : """
Custom Account Invoice
========================
This module overrides or creates printouts for accounting.

Extra features:
-------------------------------
* extra balance row in invoice
* extra currency data in invoice
* payments history in invoice
* printable Payment Vouchers
* force cancel button to appear in paid pyslips
    """,
    "data" : [ 
        "account_invoice_view.xml",
        "hr_payroll_view.xml",
        "account_voucher_view.xml",
        "custom_account_report.xml",
    ], 
    "application": False, 
    "installable": True
}


{
    "name" : "Custom EIS Modifications",
    "version" : "2.3", 
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
* batch duplicate payslips
* group payslips by month
    """,
    "data" : [ 
        "account_invoice_view.xml",
        "hr_payroll_view.xml",
        "hr_payroll_data.xml",
        "account_voucher_view.xml",
        "custom_account_report.xml",
    ], 
    "application": False, 
    "installable": True
}


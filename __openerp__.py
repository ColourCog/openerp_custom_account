{
    "name" : "Custom EIS Modifications",
    "version" : "2.9", 
    "category" : "Accounting", 
    "sequence": 60,
    "complexity" : "normal", 
    "author" : "ColourCog.com", 
    "website" : "http://colourcog.com", 
    "depends" : [
        "base", 
        "hr_payroll",
        "hr_loan",
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
    """,
    "data" : [ 
        "security/ir_rule.xml",
        "security/ir.model.access.csv",
        "account_invoice_view.xml",
        "hr_payroll_view.xml",
        "hr_payroll_data.xml",
        "hr_loan_data.xml",
        "accounting_data.xml",
        "account_voucher_view.xml",
        "custom_account_report.xml",
        "partner_view.xml",
        "purchase_data.xml",
    ], 
    "application": False, 
    "installable": True
}


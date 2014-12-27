{
    "name" : "Custom Account Invoices",
    "version" : "1.0", 
    "category" : "Accounting", 
    "sequence": 60,
    "complexity" : "normal", 
    "author" : "ColourCog.com", 
    "website" : "http://colourcog.com", 
    "depends" : [
        "base", 
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
    """,
    "data" : [ 
        "account_invoice_view.xml",
        "account_voucher_view.xml",
        "custom_account_report.xml",
    ], 
    "application": False, 
    "installable": True
}


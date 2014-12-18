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
    ], 
    "summary" : "Modifies the standard invoice reports", 
    "description" : """
Custom Account Invoice
========================
This module overwrites the default invoices printouts for accounting.

Extra features:
-------------------------------
* extra balance row
* extra currency data
    """,
    "data" : [ 
        "account_invoice_view.xml",
        "custom_account_report.xml",
    ], 
    "application": False, 
    "installable": True
}


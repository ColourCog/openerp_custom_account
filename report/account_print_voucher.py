# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from openerp.report import report_sxw
from openerp.tools import amount_to_text_en

class account_voucher(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(account_voucher, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
            'get_title': self.get_title,
            'get_on_account':self.get_on_account,
        })

    def get_title(self, type):
        title = ''
        if type:
            title = type[0].swapcase() + type[1:] + " Voucher"
        return title

    def get_on_account(self, voucher):
        name = ""
        if voucher.type == 'receipt':
            name = "Received payment from "+str(voucher.partner_id.name)
        elif voucher.type == 'payment':
            name = "Payment to "+str(voucher.partner_id.name)
        elif voucher.type == 'sale':
            name = "Sale to "+str(voucher.partner_id.name)
        elif voucher.type == 'purchase':
            name = "Purchase from "+str(voucher.partner_id.name)
        return name

report_sxw.report_sxw(
    'report.custom.account.voucher',
    'account.voucher',
    'addons/account_voucher/report/account_voucher_print.rml',
    parser=account_voucher,header="external"
)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

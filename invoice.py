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
from lxml import etree
import openerp.addons.decimal_precision as dp
import openerp.exceptions

from openerp import netsvc
from openerp import pooler
from openerp.osv import fields, osv, orm
from openerp.tools.translate import _

class account_invoice(osv.osv):
    _inherit='account.invoice'
    _name='account.invoice'

    def invoice_print(self, cr, uid, ids, context=None):
        """This function overloads the default invoice print to make sure we get """
        res = super(account_invoice, self).invoice_print( cr, uid, ids,context) #self, cr, uid, ids, context)
        res["report_name"] = "custom.account.invoice"
        return res

    def _get_extra_currency(self, cr, uid, context=None):
        res = False
        cur_obj = self.pool.get('res.currency')
        currency_ids = cur_obj.search(cr, uid, [("name","=","EUR")], context=context)
        return currency_ids[0]
        

    _columns = {
        'extra_currency_id': fields.many2one('res.currency', 'Extra Currency', required=True),
    }
    
    _defaults = {
        'extra_currency_id': _get_extra_currency
    }

account_invoice()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

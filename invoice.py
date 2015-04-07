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
from openerp.tools.amount_to_text_en import amount_to_text

class account_invoice(osv.osv):
    _inherit='account.invoice'
    _name='account.invoice'

    def invoice_print(self, cr, uid, ids, context=None):
        """This function overloads the default invoice print """
        res = super(account_invoice, self).invoice_print( cr, uid, ids,context) #self, cr, uid, ids, context)
        res["report_name"] = "custom.account.invoice"
        return res

    def _get_extra_currency(self, cr, uid, context=None):
        res = False
        cur_obj = self.pool.get('res.currency')
        currency_ids = cur_obj.search(cr, uid, [("name","=","EUR")], context=context)
        return currency_ids[0]

    def _get_cash_journal(self, cr, uid, context=None):
        res = False
        cur_obj = self.pool.get('account.journal')
        currency_ids = cur_obj.search(cr, uid, [("type","=","cash")], context=context)
        return currency_ids[0]
    
    def invoice_validate_and_pay_cash(self, cr, uid, ids, context=None):
        if not ids: return []
        dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_voucher', 'view_vendor_receipt_dialog_form')

        inv = self.browse(cr, uid, ids[0], context=context)

        wf_service = netsvc.LocalService("workflow")
        if inv.state == "draft":
            #~ wf_service.trg_validate(uid, 'account.invoice', inv.id, 'invoice_open', cr)
            self.action_date_assign(cr,uid,ids,context)
            self.action_move_create(cr,uid,ids,context=context)
            self.action_number(cr,uid,ids,context)
            self.invoice_validate(cr,uid,ids,context=context)
        #~ return {
            #~ 'name':_("Pay Invoice"),
            #~ 'view_mode': 'form',
            #~ 'view_id': view_id,
            #~ 'view_type': 'form',
            #~ 'res_model': 'account.voucher',
            #~ 'type': 'ir.actions.act_window',
            #~ 'nodestroy': True,
            #~ 'target': 'new',
            #~ 'domain': '[]',
            #~ 'context': {
                #~ 'payment_expected_currency': inv.currency_id.id,
                #~ 'default_partner_id': self.pool.get('res.partner')._find_accounting_partner(inv.partner_id).id,
                #~ 'default_amount': inv.type in ('out_refund', 'in_refund') and -inv.residual or inv.residual,
                #~ 'default_reference': inv.reference and inv.reference or inv.name,
                #~ 'default_date': inv.date_invoice,
                #~ 'default_journal_id': self._get_cash_journal(cr,uid,context=context),
                #~ 'close_after_process': True,
                #~ 'invoice_type': inv.type,
                #~ 'invoice_id': inv.id,
                #~ 'default_type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment',
                #~ 'type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment'
            #~ }
        #~ }
        return self._create_cash_voucher(cr, uid, ids, context=context)

    def _create_cash_voucher(self, cr, uid, ids, context):
        voucher_obj = self.pool.get('account.voucher')
        inv_obj = self.pool.get('account.invoice')
        journal_obj = self.pool.get('account.journal')
        move_line_obj = self.pool.get('account.move.line')
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id

        for inv in inv_obj.browse(cr, uid, ids, context=context):
            name = _('Cash Purchase by %s') % (inv.reference)
            partner_id = inv.partner_id.id
            journal = journal_obj.browse(cr, uid, self._get_cash_journal(cr,uid,context=context), context=context)
            amt = inv.residual
            credit_account_id = inv.account_id.id
            move_line_id = move_line_obj.search(cr, uid, [('move_id','=',inv.move_id.id),
                            ('invoice','=',inv.id)],context=context)[0]
            voucher = {
                'journal_id': journal.id,
                'company_id': company_id,
                'partner_id': partner_id,
                'type':'payment',
                'name': name,
                'reference': inv.reference,
                'account_id': journal.default_credit_account_id.id,
                'amount': amt > 0.0 and amt or 0.0,
                'date': inv.date_invoice,
                'date_due': inv.date_invoice,
                }

            vl = (0, 0, {
                'name': inv.name,
                'move_line_id': move_line_id,
                'reconcile': True,
                'amount': amt > 0.0 and amt or 0.0,
                'account_id': credit_account_id,
                'type': amt > 0.0 and 'dr' or 'cr',
                })
            voucher['line_ids'] = [vl]
            voucher_id = voucher_obj.create(cr, uid, voucher, context=context)
            voucher_obj.button_proforma_voucher(cr, uid, [voucher_id], context)
            inv_obj.confirm_paid(cr, uid, [inv.id], context=context)

        return True

    _columns = {
        'extra_currency_id': fields.many2one('res.currency', 'Extra Currency', required=True),
    }
    
    _defaults = {
        'extra_currency_id': _get_extra_currency
    }

account_invoice()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

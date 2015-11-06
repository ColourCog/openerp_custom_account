#-*- coding:utf-8 -*-

import time
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta

from openerp import pooler
from openerp import netsvc
from openerp.osv import fields, osv
from openerp import tools
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

from openerp.tools.safe_eval import safe_eval as eval
import logging
_logger = logging.getLogger(__name__)


class hr_loan(osv.osv):
    '''Quick loan fixes'''

    _inherit = 'hr.loan'
    
    _columns = {    
        'invoice_id': fields.many2one(
            'account.invoice',
            'Origin Invoice',
            readonly=True),
        'notes': fields.text(
            'Justification',
            readonly=True,
            states={
                'draft': [('readonly', False)],
                'confirm': [('readonly', False)]}),
    }


    def batch_reprocess_loan(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        for loan in self.browse(cr, uid, ids, context=context):
            target_state = loan.state
            self.write(cr, uid, [loan.id], {'state':'draft'}, context=context)
            wf_service.trg_delete(uid, 'hr.loan', loan.id, cr)
            wf_service.trg_create(uid, 'hr.loan', loan.id, cr)
            for state in ['draft', 'confirm', 'validate', 'waiting']:
                wf_service.trg_validate(uid, 'hr.loan', loan.id, state, cr)
                if state == target_state:
                    return ids
        return ids

    def loan_invoice(self, cr, uid, ids, context=None):
        dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'custom_account', 'hr_loan_invoice_view')

        return {
            'name': _("Import Invoice"),
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'hr.loan.invoice',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': context
        }

    def import_invoice(self, cr, uid, ids, context=None):
        """Import an invoice as basis for a loan"""
        wf_service = netsvc.LocalService("workflow")
        for loan in self.browse(cr, uid, ids, context=context):
            # we expect to get an invoice, a date and a payment method
            # first set the data
            vals = {
                'invoice_id': context.get('invoice_id'),
                'move_id': context.get('move_id'),
                'amount': context.get('amount'),
                'nb_payments': context.get('nb_payments'),
                'installment': context.get('installment'),
                'date_confirm': context.get('date'),
                'date_valid': context.get('date'),
                'user_valid': uid,
            }
            # make the payment
            vals['voucher_id'] = self._create_voucher(
                cr, 
                uid, 
                loan.id, 
                context.get('move_id'), 
                context.get('paymethod_id'), 
                _('Loan %s to %s') % (loan.name, loan.employee_id.name),
                'in', 
                _('LOAN %s') % (loan.name),
                context.get('date'),
                context.get('amount'), 
                context=context)

            self.write(
                cr, 
                uid, 
                [loan.id], 
                vals,
                context=context)
                
            # forward the workflow
            wf_service.trg_validate(uid, 'hr.loan', loan.id, 'confirm', cr)
            wf_service.trg_validate(uid, 'hr.loan', loan.id, 'validate', cr)
            wf_service.trg_validate(uid, 'hr.loan', loan.id, 'waiting', cr)

    def clean_loan(self, cr, uid, ids, context=None):
        """We are going to bypass all security and 
        recusrively cancel where needed"""
        pay_obj = self.pool.get('hr.loan.payment')
        move_obj = self.pool.get('account.move')
        voucher_obj = self.pool.get('account.voucher')
        slip_obj = self.pool.get('hr.payslip')
        for loan in self.browse(cr, uid, ids, context=context):
            if loan.invoice_id and loan.move_id:
                self.write(
                    cr, 
                    uid, 
                    [loan.id], 
                    {'invoice_id': False, 'move_id': False}, 
                    context=context)
            if loan.move_id and not loan.invoice_id:
                move_obj.unlink(
                    cr,
                    uid,
                    [loan.move_id.id],
                    context=context)
            if loan.payment_ids:
                slips = [p.slip_id.id for p in loan.payment_ids]
                slip_obj.cancel_sheet(cr, uid, slips, context=context)
                # below should not be needed
                #~ self.write(
                    #~ cr,
                    #~ uid,
                    #~ [loan.id],
                    #~ {'payment_ids': []},
                    #~ context=context)
            if loan.voucher_ids:
                vouchers = [v.id for v in loan.voucher_ids]
                voucher_obj.cancel_voucher(
                    cr,
                    uid,
                    vouchers,
                    context=context)
                # I'd rather cancel and ignore then delete and regret
                self.write(
                    cr,
                    uid,
                    [loan.id],
                    {'voucher_ids': []},
                    context=context)
            if loan.voucher_id:
                voucher_obj.cancel_voucher(
                    cr,
                    uid,
                    [loan.voucher_id.id],
                    context=context)
                # I'd rather cancel and ignore then delete and regret
                self.write(
                    cr,
                    uid,
                    [loan.id],
                    {'voucher_id': False},
                    context=context)
        

hr_loan()


class hr_loan_invoice(osv.osv_memory):
    """
    This wizard import an invoice into a loan
    """

    _name = "hr.loan.invoice"
    _description = "Import Invoice as Loan"

    def _get_partner(self, cr, uid, ctx=None):
        emp = self.pool.get('hr.employee').browse(
            cr, 
            uid, 
            ctx.get('employee_id', False), context=ctx)
        if emp.address_home_id:
            return emp.address_home_id.id
        return False

    def onchange_invoice(self, cr, uid, ids, invoice_id, context=None):
        inv = self.pool.get('account.invoice').browse(
            cr, 
            uid, 
            invoice_id, 
            context=context)
        return {'value': {'amount': inv.amount_total}}

    def onchange_nb_payments(self, cr, uid, ids, amount, nb_payments,
                                context=None):
        val = amount / nb_payments
        return {'value': {'installment': val}}


    _columns = {
        'partner_id': fields.many2one(
            'res.partner',
            'Partner',
            readonly=True),
        'invoice_id': fields.many2one(
            'account.invoice', 
            'Invoice to transfer', 
            required=True),
        'amount': fields.related(
            'invoice_id',
            'amount_total',
            string="Amount"),
        'nb_payments': fields.integer(
            'Number of payments',
            required=True),
        'installment': fields.float(
            'Due amount per payment',
            digits_compute=dp.get_precision('Payroll'),
            required=True),
        'paymethod_id': fields.many2one(
            'account.journal', 
            'Payment method', 
            required=True),
    }
    _defaults = {
        'partner_id': _get_partner,
    }

    def import_loan(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        pool_obj = pooler.get_pool(cr.dbname)
        loan_obj = pool_obj.get('hr.loan')

        context.update({
            'invoice_id': self.browse(cr, uid, ids)[0].invoice_id.id,
            'move_id': self.browse(cr, uid, ids)[0].invoice_id.move_id.id,
            'date': self.browse(cr, uid, ids)[0].invoice_id.date_invoice,
            'amount': self.browse(cr, uid, ids)[0].invoice_id.amount_total,
            'nb_payments': self.browse(cr, uid, ids)[0].nb_payments,
            'installment': self.browse(cr, uid, ids)[0].installment,
            'paymethod_id': self.browse(cr, uid, ids)[0].paymethod_id.id,
            })

        loan_obj.import_invoice(cr, uid, [context.get('active_id')], context=context)

        return {'type': 'ir.actions.act_window_close'}

hr_loan_invoice()

#~ TODO:
    #~ 1. create a tool that will import an existing invoice in a new loan.
    #~ the invoice's move become the loan's move and the invoice's payment becomes
    #~ the loan's giveout.
         
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

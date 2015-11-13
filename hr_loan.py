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
        'hidden_move_id': fields.many2one(
            'account.move', 
            'Ownership Entry',
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

            # if need be, make the ownership switch
            if context.get('employee_partner_id') != context.get('partner_id'):
                ctx = dict(context or {}, account_period_prefer_normal=True)
                move_obj = self.pool.get('account.move')
                period_obj = self.pool.get('account.period')
                journal_obj = self.pool.get('account.journal')
                company_id = loan.company_id.id
                period_id = period_obj.find(cr, uid, context.get('date'), context=ctx)[0]
                journal = journal_obj.browse(cr, uid, context.get('paymethod_id'), context=ctx)
                account_id = journal.default_debit_account_id.id
                
                vals['hidden_move_id'] =  move_obj.create(
                    cr, 
                    uid, 
                    move_obj.account_move_prepare(
                        cr, 
                        uid, 
                        loan.journal_id.id, 
                        date=context.get('date'), 
                        ref=_('LOAN %s ownership switch') % (loan.name), 
                        company_id=company_id, 
                        context=ctx),
                    context=ctx)
                    

                lml = []
                # create the debit move line
                lml.append({
                        'partner_id': context.get('partner_id'),
                        'name': loan.name,
                        'debit': context.get('amount'),
                        'account_id': account_id,
                        'date_maturity': context.get('date'),
                        'period_id': period_id,
                        })

                # create the credit move line
                lml.append({
                        'partner_id': context.get('employee_partner_id'),
                        'name': loan.name,
                        'credit': context.get('amount'),
                        'account_id': account_id,
                        'date_maturity': context.get('date'),
                        'period_id': period_id,
                        })
                # convert eml into an osv-valid format
                lines = [(0, 0, x) for x in lml]
                move_obj.write(cr, uid, [vals['hidden_move_id']], {'line_id': lines}, context=ctx)
                # post the journal entry if 'Skip 'Draft' State for Manual Entries' is checked
                if loan.journal_id.entry_posted:
                    move_obj.button_validate(cr, uid, [vals['hidden_move_id']], ctx)
            
            #ok we're done now
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
                if loan.hidden_move_id:
                    move_obj.unlink(
                        cr,
                        uid,
                        [loan.hidden_move_id.id],
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

    def onchange_employee(self, cr, uid, ids, employee_partner_id, context=None):
        return {'value': {'partner_id': employee_partner_id}}

    def onchange_invoice(self, cr, uid, ids, invoice_id, context=None):
        inv = self.pool.get('account.invoice').browse(
            cr, 
            uid, 
            invoice_id, 
            context=context)
        return {'value': {'amount': inv.amount_total}}

    def onchange_amount(self, cr, uid, ids, amount, nb_payments,
                        context=None):
        val = amount / nb_payments
        return {'value': {'installment': val}}

    def onchange_nb_payments(self, cr, uid, ids, amount, nb_payments,
                                context=None):
        return self.onchange_amount(
                cr,
                uid,
                ids,
                amount,
                nb_payments,
                context=context)


    _columns = {
        'employee_partner_id': fields.many2one(
            'res.partner',
            'Employee Partner'),
        'partner_id': fields.many2one(
            'res.partner',
            'Partner'),
        'invoice_id': fields.many2one(
            'account.invoice', 
            'Invoice to transfer', 
            required=True),
        'amount': fields.integer(
            'Amount',
            required=True),
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
        'employee_partner_id': _get_partner,
        'nb_payments': 1,
    }

    def import_loan(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        pool_obj = pooler.get_pool(cr.dbname)
        loan_obj = pool_obj.get('hr.loan')

        context.update({
            'employee_partner_id': self.browse(cr, uid, ids)[0].employee_partner_id.id,
            'partner_id': self.browse(cr, uid, ids)[0].partner_id.id,
            'invoice_id': self.browse(cr, uid, ids)[0].invoice_id.id,
            'move_id': self.browse(cr, uid, ids)[0].invoice_id.move_id.id,
            'date': self.browse(cr, uid, ids)[0].invoice_id.date_invoice,
            'amount': self.browse(cr, uid, ids)[0].amount,
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

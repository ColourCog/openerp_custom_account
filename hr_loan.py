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

class res_company(osv.osv):
    _inherit = "res.company"

    _columns = {
        'default_loan_invoice_journal_id': fields.many2one('account.journal',
            'The Invoice Payment method to use by default'),
    }

res_company()

class hr_config_settings(osv.osv_memory):
    _inherit = 'hr.config.settings'

    _columns = {
        'default_loan_invoice_journal_id': fields.related(
            'company_id',
            'default_loan_invoice_journal_id',
            type='many2one',
            relation='account.journal',
            string="Invoice/Loan payment method"),
    }

    def onchange_company_id(self, cr, uid, ids, company_id, context=None):
        # update related fields
        val = super(hr_config_settings, self).onchange_company_id(cr, uid, ids, company_id, context=context)
        if 'value' in val:
            values = val.get('value')
            values.update({
                'default_loan_invoice_journal_id': False,
            })
            if company_id:
                company = self.pool.get('res.company').browse(cr, uid, company_id, context=context)
                values.update({
                    'default_loan_invoice_journal_id': company.default_loan_invoice_journal_id and company.default_loan_invoice_journal_id.id or False,
                })
        return {'value': values}


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
                'amount': context.get('amount'),
                'nb_payments': context.get('nb_payments'),
                'installment': context.get('installment'),
                'date_confirm': context.get('date'),
                'date_valid': context.get('date'),
                'user_valid': uid,
                'is_advance': False, #no way this is an advance!
            }

            vals['move_id'] = self._create_move(
                cr, 
                uid, 
                loan.id,
                loan.name,
                loan.account_credit.id,
                loan.account_debit.id,
                context.get('date'),
                context.get('amount'),
                context=context)

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
                        'partner_id': context.get('employee_partner_id'),
                        'name': loan.name,
                        'debit': context.get('amount'),
                        'account_id': account_id,
                        'date_maturity': context.get('date'),
                        'period_id': period_id,
                        })

                # create the credit move line
                lml.append({
                        'partner_id': context.get('partner_id'),
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

    def loan_voucher(self, cr, uid, ids, context=None):
        for rec in self.browse(cr, uid, ids, context=context):
            if rec.voucher_id:
                raise osv.except_osv(
                    _('Error'),
                    _('This loan already has a Give-Out Voucher'))

        dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'custom_account', 'hr_loan_voucher_view')

        return {
            'name': _("Import Voucher"),
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'hr.loan.voucher',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': context
        }

    def import_voucher(self, cr, uid, ids, context=None):
        """Import a voucher as loan give-out"""
        wf_service = netsvc.LocalService("workflow")
        for loan in self.browse(cr, uid, ids, context=context):
            vals = {
                'voucher_id': context.get('voucher_id'),
            }
            if loan.employee_id.address_home_id.id != context.get('partner_id'):
                raise osv.except_osv(
                    _('Wrong Employee'),
                    _("Selected voucher's partner does not match employee '%s'!" % loan.employee_id.name))
            if loan.amount != context.get('amount'):
                raise osv.except_osv(
                    _('Wrong amount'),
                    _("Selected voucher's amount does not match loan!" ))

            #create a new move_id. This is safe as if skips if exists
            self.action_receipt_create(cr, uid, [loan.id], context=context)

            #TODO: we need to discard any existing line_ids and recreate them
            # using this loan. so if the loan doesn't yet have a move_id,
            # we need to create it.
            move_obj = self.pool.get('account.move')
            move_line_obj = self.pool.get('account.move.line')
            voucher_obj = self.pool.get('account.voucher')
            voucher_line_obj = self.pool.get('account.voucher.line')
            move = loan.move_id
            if move:
                # Define the voucher line
                lml = []
                #order the lines by most old first
                mlids = [l.id for l in move.line_id]
                mlids.reverse()
                # Create voucher_lines
                rec_ids = []
                account_move_lines = move_line_obj.browse(cr, uid, mlids, context=context)
                account_id = None
                for line_id in account_move_lines:
                    if line_id.debit:
                        continue
                    account_id = line_id.account_id.id
                    if not line_id.reconcile_id:
                        rec_ids.append(line_id.id)
                    lml.append({
                        'name': line_id.name,
                        'move_line_id': line_id.id,
                        'reconcile': (line_id.credit <= loan.amount),
                        'amount': line_id.credit < loan.amount and line_id.credit or max(0, loan.amount),
                        'account_id': account_id,
                        'type': 'dr',
                        })
                lines = [(0, 0, x) for x in lml]
                # alright we have the lines. Now let's check if we have the right to move on
                voucher = voucher_obj.browse(cr, uid, context.get('voucher_id'), context)
                # now we need to recreate the reconcile if need be (voucher is not draft)
                if rec_ids and voucher.move_id:
                    for line in voucher.move_id.line_id:
                        if line.reconcile_id:
                            raise osv.except_osv(
                                _('Reconciliation Error'),
                                _("Selected Voucher already reconciles another Journal Item" ))
                        if line.account_id.id == account_id:
                            rec_ids.append(line.id)
                    # check again that we can reconcile
                    if len(rec_ids) < 2:
                        raise osv.except_osv(
                            _('Reconciliation Error'),
                            _("Selected Voucher does not match Loan's account" ))
                    # all good, we can proceed
                    voucher_line_obj.unlink(cr, uid, [n.id for n in voucher.line_ids], context)
                    voucher_obj.write(cr, uid, [voucher.id], {'line_ids': lines}, context)
                    # and reconcile
                    reconcile = move_line_obj.reconcile_partial(cr, uid, rec_ids, writeoff_acc_id=voucher.writeoff_acc_id.id, writeoff_period_id=voucher.period_id.id, writeoff_journal_id=voucher.journal_id.id)

            #ok we're ready
            self.write(
                cr,
                uid,
                [loan.id],
                vals,
                context=context)

            wf_service.trg_validate(uid, 'hr.loan', loan.id, 'validate', cr)
            wf_service.trg_validate(uid, 'hr.loan', loan.id, 'waiting', cr)


    def clean_loan(self, cr, uid, ids, context=None):
        """We are going to bypass all security and
        recursively cancel where needed"""
        pay_obj = self.pool.get('hr.loan.payment')
        move_obj = self.pool.get('account.move')
        voucher_obj = self.pool.get('account.voucher')
        slip_obj = self.pool.get('hr.payslip')
        for loan in self.browse(cr, uid, ids, context=context):
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
            if loan.move_ids:
                l = [p.id for p in loan.move_ids]
                move_obj.unlink(cr, uid, l, context=context)
                self.write(
                    cr,
                    uid,
                    [loan.id],
                    {'move_ids': []},
                    context=context)

hr_loan()


class hr_loan_invoice(osv.osv_memory):
    """
    This wizard import an invoice into a loan
    """

    _name = "hr.loan.invoice"
    _description = "Import Invoice as Loan"

    def _get_partner(self, cr, uid, ctx=None):
        if not ctx.get('employee_id'):
            return False
        emp = self.pool.get('hr.employee').browse(
            cr,
            uid,
            ctx.get('employee_id'), context=ctx)
        if emp.address_home_id:
            return emp.address_home_id.id
        return False

    def _get_journal(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id.default_loan_invoice_journal_id:
            return user.company_id.default_loan_invoice_journal_id.id
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
            'Loan payment method',
            required=True),
    }
    _defaults = {
        'employee_partner_id': _get_partner,
        'paymethod_id': _get_journal,
        'nb_payments': 1,
    }

    def import_invoice(self, cr, uid, ids, context=None):
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

class hr_loan_voucher(osv.osv_memory):
    """
    This wizard import an voucher into a loan
    """

    _name = "hr.loan.voucher"
    _description = "Import Voucher as Loan Give-Out"

    def _get_partner(self, cr, uid, ctx=None):
        if not ctx.get('employee_id'):
            return False
        emp = self.pool.get('hr.employee').browse(
            cr,
            uid,
            ctx.get('employee_id'), context=ctx)
        if emp.address_home_id:
            return emp.address_home_id.id
        return False

    def onchange_employee(self, cr, uid, ids, employee_partner_id, context=None):
        return {'value': {'partner_id': employee_partner_id}}

    def onchange_voucher(self, cr, uid, ids, voucher_id, context=None):
        voucher = self.pool.get('account.voucher').browse(
            cr,
            uid,
            voucher_id,
            context=context)
        return {'value': {'amount': voucher.amount}}


    _columns = {
        'employee_partner_id': fields.many2one(
            'res.partner',
            'Employee Partner'),
        'partner_id': fields.many2one(
            'res.partner',
            'Partner'),
        'voucher_id': fields.many2one(
            'account.voucher',
            'Voucher to use',
            required=True),
        'amount': fields.integer(
            'Amount',
            required=True),
    }
    _defaults = {
        'employee_partner_id': _get_partner,
    }

    def import_voucher(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        pool_obj = pooler.get_pool(cr.dbname)
        loan_obj = pool_obj.get('hr.loan')

        context.update({
            'employee_partner_id': self.browse(cr, uid, ids)[0].employee_partner_id.id,
            'partner_id': self.browse(cr, uid, ids)[0].partner_id.id,
            'voucher_id': self.browse(cr, uid, ids)[0].voucher_id.id,
            'amount': self.browse(cr, uid, ids)[0].amount,
            })

        loan_obj.import_voucher(cr, uid, [context.get('active_id')], context=context)

        return {'type': 'ir.actions.act_window_close'}

hr_loan_voucher()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

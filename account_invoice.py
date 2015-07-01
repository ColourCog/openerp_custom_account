# -*- coding: utf-8 -*-

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc


class account_invoice(osv.osv):
    _inherit = 'account.invoice'
    _name = 'account.invoice'

    def invoice_print(self, cr, uid, ids, context=None):
        """This function overloads the default invoice print """
        res = super(account_invoice, self).invoice_print(
                    cr,
                    uid,
                    ids,
                    context)  # self, cr, uid, ids, context)
        res["report_name"] = "custom.account.invoice"
        return res

    def _get_extra_currency(self, cr, uid, context=None):
        cur_obj = self.pool.get('res.currency')
        currency_ids = cur_obj.search(
            cr,
            uid,
            [("name", "=", "EUR")],
            context=context)
        return currency_ids[0]

    def _get_cash_journal(self, cr, uid, context=None):
        cur_obj = self.pool.get('account.journal')
        currency_ids = cur_obj.search(
            cr,
            uid,
            [("type", "=", "cash")],
            context=context)
        return currency_ids[0]

    def correct_invoice_date(self, cr, uid, ids, context=None):
        order_obj = self.pool.get('purchase.order')

        for inv in self.browse(cr, uid, ids, context=context):
            if not inv.origin:
                continue
            order_id = order_obj.search(
                cr,
                uid,
                [('name', '=', inv.origin)],
                context=context)
            order = order_obj.browse(cr, uid, order_id, context=context)[0]
            self.write(
                cr,
                uid,
                [inv.id],
                {'date_invoice': order.date_order},
                context=context)
        return ids

    def invoice_validate_and_pay_cash(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService('workflow')
        if context is None:
            context = {}
        if not ids:
            return []
        for inv in self.browse(cr, uid, ids, context=context):
            if inv.state not in ('draft', 'proforma', 'proforma2'):
                raise osv.except_osv(
                    _('Warning!'),
                    _("Selected invoice(s) cannot be confirmed as they are not in 'Draft' or 'Pro-Forma' state."))
            wf_service.trg_validate(
                    uid,
                    'account.invoice',
                    inv.id,
                    'invoice_open',
                    cr)
        return self._create_cash_voucher(cr, uid, ids, context=context)

    def _create_cash_voucher(self, cr, uid, ids, context):
        ctx = context.copy()
        ctx.update({'account_period_prefer_normal': True})

        voucher_obj = self.pool.get('account.voucher')
        inv_obj = self.pool.get('account.invoice')
        journal_obj = self.pool.get('account.journal')
        move_line_obj = self.pool.get('account.move.line')
        period_obj = self.pool.get('account.period')
        company_id = self.pool.get('res.users').browse(
            cr,
            uid,
            uid,
            context=ctx).company_id.id

        for inv in inv_obj.browse(cr, uid, ids, context=ctx):
            name = _('Cash Purchase by %s') % (inv.reference)
            partner_id = inv.partner_id.id
            journal = journal_obj.browse(
                cr,
                uid,
                self._get_cash_journal(
                    cr,
                    uid,
                    context=ctx),
                context=ctx)
            amt = inv.residual
            credit_account_id = inv.account_id.id
            move_line_id = move_line_obj.search(
                cr,
                uid,
                [('move_id', '=', inv.move_id.id),
                    ('invoice', '=', inv.id)],
                context=ctx)[0]
            voucher = {
                'journal_id': journal.id,
                'company_id': company_id,
                'partner_id': partner_id,
                'type': 'payment',
                'name': name,
                'reference': inv.reference,
                'account_id': journal.default_credit_account_id.id,
                'amount': amt > 0.0 and amt or 0.0,
                'date': inv.date_invoice,
                'date_due': inv.date_invoice,
                'period_id': period_obj.find(
                    cr,
                    uid,
                    inv.date_invoice,
                    context=ctx)[0],
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
            voucher_id = voucher_obj.create(
                cr,
                uid,
                voucher,
                context=ctx)
            voucher_obj.button_proforma_voucher(
                cr,
                uid,
                [voucher_id],
                context)
            inv_obj.confirm_paid(cr, uid, [inv.id], context=ctx)

        return True

    _columns = {
        'extra_currency_id': fields.many2one(
                                'res.currency',
                                'Extra Currency',
                                required=True),
    }

    _defaults = {
        'extra_currency_id': _get_extra_currency
    }

account_invoice()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

# -*- coding: utf-8 -*-

from openerp.osv import fields, osv
from openerp.tools.translate import _


class account_move_line(osv.osv):
    _inherit = 'account.move.line'
    _name = 'account.move.line'

    def correct_move_period(self, cr, uid, ids, context=None):
        period_obj = self.pool.get('account.period')
        reconcile_pool = self.pool.get('account.move.reconcile')
        move_line_pool = self.pool.get('account.move.line')

        for line in self.browse(cr, uid, ids, context=context):
            period_id = period_obj.find(cr, uid, line.date, context=context)[0]
            if line.period_id.id == period_id:
                continue
            move_lines = []
            to_reconcile = False
            # Unreconcile first
            if line.reconcile_id:
                to_reconcile = True
                move_lines = [move_line.id for move_line in line.reconcile_id.line_id]
                move_lines.remove(line.id)
                reconcile_pool.unlink(cr, uid, [line.reconcile_id.id])
                if len(move_lines) >= 2:
                    move_line_pool.reconcile_partial(cr, uid, move_lines, 'auto',context=context)
            # now correct the period id
            self.write(
                cr,
                uid,
                [line.id],
                {'period_id': period_id},
                context=context)
            # finally reconcile again if need be:
            if to_reconcile:
                if len(move_lines) >= 2:
                    reconcile_pool.unlink(
                            cr,
                            uid,
                            [move_lines[0].reconcile_id.id])
                move_lines.append(line.id)
                move_line_pool.reconcile(cr, uid, move_lines, 'auto',context=context)
        return ids


account_move_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

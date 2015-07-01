# -*- coding: utf-8 -*-

from openerp.osv import osv


class account_move_line(osv.osv):
    _inherit = 'account.move.line'
    _name = 'account.move.line'

    def correct_move_period(self, cr, uid, ids, context=None):
        period_obj = self.pool.get('account.period')
        reconcile_pool = self.pool.get('account.move.reconcile')
        skip_list = []
        ctx = context.copy()
        ctx.update({'account_period_prefer_normal': True})

        for line in self.browse(cr, uid, ids, context=context):
            if line.id in skip_list:
                continue
            period_id = period_obj.find(cr, uid, line.date, context=ctx)[0]
            if line.period_id.id == period_id:
                continue
            move_lines = []
            to_reconcile = False
            # Unreconcile first
            if line.reconcile_id:
                to_reconcile = True
                move_lines = [
                    move_line.id
                    for move_line
                    in line.reconcile_id.line_id]
                reconcile_pool.unlink(cr, uid, [line.reconcile_id.id])
            # now correct the period id
            self.write(
                cr,
                uid,
                move_lines,
                {'period_id': period_id},
                context=ctx,
                update_check=False)
            # finally reconcile again if need be:
            if to_reconcile:
                self.reconcile(
                        cr,
                        uid,
                        move_lines,
                        'auto',
                        context=ctx)
            skip_list.extend(move_lines)
        return ids


account_move_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

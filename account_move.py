# -*- coding: utf-8 -*-

from openerp.osv import osv


class account_move(osv.osv):
    _inherit = 'account.move'
    _name = 'account.move'

    def correct_move_period(self, cr, uid, ids, context=None):
        period_obj = self.pool.get('account.period')
        move_line_obj = self.pool.get('account.move.line')
        reconcile_pool = self.pool.get('account.move.reconcile')
        ctx = context.copy()
        ctx.update({'account_period_prefer_normal': True})
        to_reconcile = []
        for move in self.browse(cr, uid, ids, context=context):
            period_id = period_obj.find(cr, uid, move.date, context=ctx)[0]
            if move.period_id.id == period_id:
                continue
            move_lines = []
            for line in move.line_id:
                # Unreconcile first
                line.refresh()
                if line.reconcile_id:
                    move_lines = [
                        move_line.id
                        for move_line
                        in line.reconcile_id.line_id]
                    if move_lines not in to_reconcile:
                        to_reconcile.append(move_lines)
                    reconcile_pool.unlink(cr, uid, [line.reconcile_id.id])
            # now correct the period id
            self.write(
                cr,
                uid,
                [line.move_id.id],
                {'period_id': period_id},
                context=ctx)
        # finally reconcile again if need be:
        for moves in to_reconcile:
            move_line_obj.reconcile(
                    cr,
                    uid,
                    moves,
                    'auto',
                    context=ctx)
        return ids


account_move()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

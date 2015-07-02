# -*- coding: utf-8 -*-

from openerp.osv import osv


class account_move_line(osv.osv):
    _inherit = 'account.move.line'
    _name = 'account.move.line'

    def correct_move_line_period(self, cr, uid, ids, context=None):
        period_obj = self.pool.get('account.period')
        move_obj = self.pool.get('account.move')
        reconcile_pool = self.pool.get('account.move.reconcile')
        skip_list = []
        ctx = context.copy()
        ctx.update({'account_period_prefer_normal': True})
        to_reconcile = []
        rec_kill = []
        move_ids = []
        for line in self.browse(cr, uid, ids, context=context):
            if line.id in skip_list:
                continue
            period_id = period_obj.find(cr, uid, line.date, context=ctx)[0]
            if line.period_id.id == period_id:
                continue
            move_lines = []
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
            #self.write(
            #    cr,
            #    uid,
            #    move_lines,
            #    {'period_id': period_id},
            #    context=ctx,
            #    update_check=False)
            move_obj.write(
                cr,
                uid,
                [line.move_id.id],
                {'period_id': period_id},
                context=ctx)
            skip_list.extend(line.move_id.line_id)
        # finally reconcile again if need be:
        for moves in to_reconcile:
            self.reconcile(
                    cr,
                    uid,
                    moves,
                    'auto',
                    context=ctx)
        return ids


account_move_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

#-*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    d$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta

from openerp import netsvc
from openerp.osv import fields, osv
from openerp import pooler
from openerp import tools
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

from openerp.tools.safe_eval import safe_eval as eval
import logging
_logger = logging.getLogger(__name__)



class hr_payslip_line(osv.osv):
    _inherit = 'hr.payslip.line'

    _columns = {
        'quantity': fields.float('Quantity', digits_compute=dp.get_precision('Account')),
    }
hr_payslip_line()

class hr_payslip(osv.osv):
    '''
    Pay Slip
    '''
    _inherit = 'hr.payslip'

    def cancel_sheet(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        for payslip in self.browse(cr, uid, ids, context=context):
            super(hr_payslip, self).cancel_sheet(cr, uid, [payslip.id], context=context)
            wf_service.trg_delete(uid, 'hr.payslip', payslip.id, cr)            
            wf_service.trg_create(uid, 'hr.payslip', payslip.id, cr)            
        return ids

    def batch_confirm(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        for payslip in self.browse(cr, uid, ids, context=context):
            if payslip.state == "draft":
                wf_service.trg_validate(uid, 'hr.payslip', payslip.id, 'hr_verify_sheet', cr)
                wf_service.trg_validate(uid, 'hr.payslip', payslip.id, 'process_sheet', cr)
        return ids

    def copy(self, cr, uid, slip_id, default=None, context=None):
        """We need to copy the input lines as well"""
        if not default:
            default = {}
        employee_obj = self.pool.get('hr.employee')
        ttyme = datetime.fromtimestamp(time.mktime(time.strptime(time.strftime('%Y-%m-01'), "%Y-%m-%d")))
        if context.get('date_from'):
            ttyme = datetime.fromtimestamp(time.mktime(time.strptime(context.get('date_from'), "%Y-%m-%d")))
        old_slip = self.browse(cr, uid, slip_id, context=context)
        employee_id = employee_obj.browse(cr, uid, old_slip.employee_id.id, context=context)
        default.update({
            'name': _('Salary Slip of %s for %s') % (employee_id.name, tools.ustr(ttyme.strftime('%B-%Y'))),
            'date_from': context.get('date_from', time.strftime('%Y-%m-01')),
            'date_to':  context.get('date_to',
                            str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10]),
            })
        new_id = super(hr_payslip, self).copy(cr, uid, slip_id, default, context=context)
        # let's compute the sheet while we're at it
        self.compute_sheet(cr, uid, [new_id], context=context)
        return new_id

    def batch_duplicate(self, cr, uid, ids, context=None):
        #~ for payslip in self.browse(cr, uid, ids, context=context):
            #~ self.copy(cr, uid, payslip.id, default=None, context=context)
        #~ return ids
        dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'custom_account', 'hr_payslip_duplicate_view')

        return {
            'name':_("Duplicate Payslips"),
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'hr.payslip.duplicate',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': context
        }
        
hr_payslip()

class hr_payslip_duplicate(osv.osv_memory):
    """
    This wizard will confirm the all the selected draft invoices
    """

    _name = "hr.payslip.duplicate"
    _description = "Duplicate the selected playslips"
    
    _columns = { 
        'date_from': fields.date('From'),
        'date_to': fields.date('To'),
    } 
    
    _defaults = {
        'date_from': time.strftime('%Y-%m-01'),
        'date_to':  str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
    }

    def duplicate_slips(self, cr, uid, ids, context=None):
        ttyme = datetime.fromtimestamp(time.mktime(time.strptime(time.strftime('%Y-%m-01'), "%Y-%m-%d")))
        wf_service = netsvc.LocalService('workflow')
        if context is None:
            context = {}
        pool_obj = pooler.get_pool(cr.dbname)
        slip_obj = pool_obj.get('hr.payslip')
        data_inv = slip_obj.read(cr, uid, context['active_ids'], ['state'], context=context)
        
        context.update({
            'date_from': self.browse(cr,uid,ids)[0].date_from,
            'date_to': self.browse(cr,uid,ids)[0].date_to,})
        
        for record in data_inv:
            slip_obj.copy(cr, uid, record['id'], default=None, context=context)
        return {'type': 'ir.actions.act_window_close'}

hr_payslip_duplicate()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

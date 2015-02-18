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
from openerp import tools
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

from openerp.tools.safe_eval import safe_eval as eval


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
        return True

    def batch_confirm(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        for payslip in self.browse(cr, uid, ids, context=context):
            if payslip.state == "draft":
                wf_service.trg_validate(uid, 'hr.payslip', payslip.id, 'hr_verify_sheet', cr)
                wf_service.trg_validate(uid, 'hr.payslip', payslip.id, 'process_sheet', cr)
        return ids
        
hr_payslip()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

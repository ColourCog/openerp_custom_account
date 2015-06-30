#-*- coding:utf-8 -*-

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
import logging
_logger = logging.getLogger(__name__)


class hr_loan(osv.osv):
    '''Quick loan fixes'''

    _inherit = 'hr.loan'


    def batch_reprocess_loan(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        for loan in self.browse(cr, uid, ids, context=context):
            self.write(cr, uid, [loan.id], {'state':'draft'}, context=context)
            wf_service.trg_delete(uid, 'hr.loan', loan.id, cr)
            wf_service.trg_create(uid, 'hr.loan', loan.id, cr)
            wf_service.trg_validate(uid, 'hr.loan', loan.id, 'draft', cr)
            wf_service.trg_validate(uid, 'hr.loan', loan.id, 'confirm', cr)
            wf_service.trg_validate(uid, 'hr.loan', loan.id, 'validate', cr)
            wf_service.trg_validate(uid, 'hr.loan', loan.id, 'waiting', cr)
        return ids


hr_loan()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

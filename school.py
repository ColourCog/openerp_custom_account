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

class school_academic_year(osv.osv):
    _name = 'school.academic.year'
    _inherit = 'school.academic.year'

    _columns = {
        'report_type': fields.selection([
            ('infant', 'Infant Report'),
            ('junior', 'Junior Report'),
            ('senior', 'Senior Report')],
            'Type of report to use',
            required=True),
    }
    _defaults = {
        'report_type': 'junior',
    }

school_academic_year()

class school_student(osv.osv):
    _name = 'school.student'
    _inherit = 'school.student'

    def batch_reprocess_workflow(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        for student in self.browse(cr, uid, ids, context=context):
            target_state = student.state
            #~ self.write(cr, uid, [student.id], {'state':'draft'}, context=context)
            wf_service.trg_delete(uid, 'school.student', student.id, cr)
            wf_service.trg_create(uid, 'school.student', student.id, cr)
            for state in ['draft', 'student', 'enrolled', 'suspend']:
                wf_service.trg_validate(uid, 'school.student', student.id, state, cr)
                if state == target_state:
                    continue
        return ids

    _columns = {
        'invoice_ids': fields.one2many(
            'account.invoice',
            'student_id',
            'Invoice history',
            readonly=True),
    }

    def student_suspend(self, cr, uid, ids, context=None):
        for student in self.browse(cr, uid, ids):
            if student.invoice_id:
                #move current reg invoice to history
                vals = {
                    'invoice_ids': [(4, student.invoice_id.id)],
                    'invoice_id': None,
                    'is_invoiced': False,
                }
                self.write(cr, uid, [student.id], vals, context=context)
        return super(school_student, self).student_suspend(cr, uid, ids, context=context)

school_student()


class school_enrolment(osv.osv):
    _name = 'school.enrolment'
    _inherit = 'school.enrolment'
    _columns = {
        'invoice_ids': fields.one2many(
            'account.invoice',
            'enrolment_id',
            'Invoice history',
            readonly=True),
    }
school_enrolment()


class account_invoice(osv.osv):
    _inherit = 'account.invoice'
    _name = 'account.invoice'
    _columns = {
        'student_id': fields.many2one(
            'school.student',
            'Student'),
        'enrolment_id': fields.many2one(
            'school.enrolment',
            'Enrolment'),
    }
account_invoice()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

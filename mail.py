# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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

import base64
import logging
import re
from email.utils import formataddr
from urllib import urlencode
from urlparse import urljoin

from openerp import tools
from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.osv.orm import except_orm
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


class mail_mail(osv.Model):
    """ Model holding RFC2822 email messages to send. This model also provides
        facilities to queue and send new email messages.  """
    _inherit = 'mail.mail'

    def send_get_email_dict(self, cr, uid, mail, partner=None, context=None):
        """ Return a dictionary for specific email values, depending on a
            partner, or generic to the whole recipients given by mail.email_to.

            :param browse_record mail: mail.mail browse_record
            :param browse_record partner: specific recipient partner
        """
        body = self.send_get_mail_body(cr, uid, mail, partner=partner, context=context)
        subject = self.send_get_mail_subject(cr, uid, mail, partner=partner, context=context)
        reply_to = self.send_get_mail_reply_to(cr, uid, mail, partner=partner, context=context)
        body_alternative = tools.html2plaintext(body)

        # generate email_to, heuristic:
        # 1. if 'partner' is specified and there is a related document: Followers of 'Doc' <email>
        # 2. if 'partner' is specified, but no related document: Partner Name <email>
        # 3; fallback on mail.email_to that we split to have an email addresses list
        if partner and mail.record_name:
            email_to = [formataddr((_('Followers of %s') % mail.record_name, partner.email))]
        elif partner:
            email_to = [formataddr((partner.name, partner.email))]
            if partner.extra_email:
                _logger.warning("also sending mail to %s" % partner.extra_email)
                email_to.append(formataddr((partner.name, partner.extra_email)))
            _logger.warning("email_to: %s" % email_to)
        else:
            email_to = tools.email_split(mail.email_to)

        return {
            'body': body,
            'body_alternative': body_alternative,
            'subject': subject,
            'email_to': email_to,
            'reply_to': reply_to,
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

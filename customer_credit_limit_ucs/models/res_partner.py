# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    active_credit_limit = fields.Boolean(
        string="Active Credit Limit",
        help="Enable to activate credit limit check for this customer."
    )
    credit_limit_amount = fields.Float(
        string="Credit Limit",
        help="The maximum credit amount allowed for this customer."
    )

    @api.constrains('active_credit_limit', 'credit_limit_amount')
    def _check_credit_limit_amount(self):
        for partner in self:
            if partner.active_credit_limit and partner.credit_limit_amount <= 0.0:
                raise ValidationError(
                    _("The Credit Limit must be greater than zero when 'Active Credit Limit' is enabled.")
                )

    def write(self, vals):
        credit_fields = {'active_credit_limit', 'credit_limit_amount'}
        if credit_fields.intersection(vals.keys()):
            if not self.env.user.has_group('sales_team.group_sale_manager'):
                raise AccessError(
                    _("Only Sales Administrators are allowed to modify the Credit Limit settings.")
                )
        return super().write(vals)


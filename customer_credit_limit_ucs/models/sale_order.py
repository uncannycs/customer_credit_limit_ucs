# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    credit_limit_approved = fields.Boolean(
        string="Credit Limit Approved",
        default=False,
        copy=False,
        help="Indicates if this sale order was approved by a manager to bypass the credit limit."
    )

    def action_confirm(self):
        for order in self:
            commercial_partner = order.partner_id.commercial_partner_id
            if commercial_partner and commercial_partner.active_credit_limit and not order.credit_limit_approved:
                exposure = order._get_credit_exposure()
                limit = commercial_partner.credit_limit_amount
                if exposure > limit:
                    return order._action_open_credit_limit_warning_wizard()
        return super(SaleOrder, self).action_confirm()

    def _get_receivables(self, commercial_partner, company):
        unpaid_invoices = self.env['account.move'].search([
            ('commercial_partner_id', '=', commercial_partner.id),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('move_type', 'in', ('out_invoice', 'out_refund')),
        ])
        receivables = 0.0
        for inv in unpaid_invoices:
            receivables += inv.currency_id._convert(
                inv.amount_residual,
                company.currency_id,
                company,
                inv.invoice_date or fields.Date.today()
            )
        return receivables

    def _get_credit_exposure(self):
        self.ensure_one()
        commercial_partner = self.partner_id.commercial_partner_id
        company = self.company_id or self.env.company

        receivables = self._get_receivables(commercial_partner, company)
        
        pending_orders = self.env['sale.order'].search([
            ('partner_id.commercial_partner_id', '=', commercial_partner.id),
            ('state', 'in', ('sale', 'done')),
            ('invoice_status', 'in', ('no', 'to invoice')),
            ('id', '!=', self.id)
        ])

        pending_amount = 0.0
        for order in pending_orders:
            pending_amount += order.currency_id._convert(
                order.amount_total,
                company.currency_id,
                company,
                order.date_order or fields.Date.today()
            )
            
        current_amount = self.currency_id._convert(
            self.amount_total,
            company.currency_id,
            company,
            self.date_order or fields.Date.today()
        )
        
        return receivables + pending_amount + current_amount

    def _action_open_credit_limit_warning_wizard(self):
        self.ensure_one()
        commercial_partner = self.partner_id.commercial_partner_id
        
        pending_orders = self.env['sale.order'].search([
            ('partner_id.commercial_partner_id', '=', commercial_partner.id),
            ('state', 'in', ('sale', 'done')),
            ('invoice_status', 'in', ('no', 'to invoice')),
            ('id', '!=', self.id)
        ])
        
        unpaid_invoices = self.env['account.move'].search([
            ('commercial_partner_id', '=', commercial_partner.id),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('move_type', 'in', ('out_invoice', 'out_refund'))
        ])
        
        ctx = dict(self.env.context)
        ctx.update({
            'default_sale_order_id': self.id,
            'default_uninvoiced_order_ids': [(6, 0, pending_orders.ids)],
            'default_unpaid_invoice_ids': [(6, 0, unpaid_invoices.ids)],
        })
        return {
            'name': _('Credit Limit Exceeded Warning'),
            'type': 'ir.actions.act_window',
            'res_model': 'credit.limit.warning.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': ctx,
        }

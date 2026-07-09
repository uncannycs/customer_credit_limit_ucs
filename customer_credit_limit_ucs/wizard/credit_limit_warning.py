# -*- coding: utf-8 -*-

from markupsafe import Markup
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CreditLimitWarningWizard(models.TransientModel):
    _name = 'credit.limit.warning.wizard'
    _description = 'Credit Limit Warning Wizard'

    sale_order_id = fields.Many2one('sale.order', string="Sale Order", required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string="Customer", related='sale_order_id.partner_id')
    currency_id = fields.Many2one('res.currency', string="Currency", related='sale_order_id.company_id.currency_id')

    credit_limit = fields.Monetary(string="Credit Limit", compute='_compute_details', currency_field='currency_id', compute_sudo=True)
    total_receivables = fields.Monetary(string="Total Receivables", compute='_compute_details', currency_field='currency_id', compute_sudo=True)
    pending_orders_amount = fields.Monetary(string="Pending Orders Amount", compute='_compute_details', currency_field='currency_id', compute_sudo=True)
    current_order_amount = fields.Monetary(string="Current Order Amount", compute='_compute_details', currency_field='currency_id', compute_sudo=True)
    total_exposure = fields.Monetary(string="Total Exposure", compute='_compute_details', currency_field='currency_id', compute_sudo=True)
    exceeded_amount = fields.Monetary(string="Exceeded Amount", compute='_compute_details', currency_field='currency_id', compute_sudo=True)

    uninvoiced_order_ids = fields.Many2many('sale.order', string="Pending Orders")
    unpaid_invoice_ids = fields.Many2many('account.move', string="Unpaid Invoices")

    is_manager = fields.Boolean(string="Is Manager", compute='_compute_is_manager')

    @api.depends('sale_order_id')
    def _compute_details(self):
        for wizard in self:
            order = wizard.sale_order_id.sudo()
            if not order:
                wizard.credit_limit = 0.0
                wizard.total_receivables = 0.0
                wizard.pending_orders_amount = 0.0
                wizard.current_order_amount = 0.0
                wizard.total_exposure = 0.0
                wizard.exceeded_amount = 0.0
                continue

            commercial_partner = order.partner_id.commercial_partner_id
            company = order.company_id or self.env.company
            wizard.credit_limit = commercial_partner.credit_limit_amount

            unpaid_invoices = self.env['account.move'].sudo().search([
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
            wizard.total_receivables = receivables

            pending_orders = self.env['sale.order'].sudo().search([
                ('partner_id.commercial_partner_id', '=', commercial_partner.id),
                ('state', 'in', ('sale', 'done')),
                ('invoice_status', 'in', ('no', 'to invoice')),
                ('id', '!=', order.id),
            ])
            pending_amount = 0.0
            for po in pending_orders:
                pending_amount += po.currency_id._convert(
                    po.amount_total,
                    company.currency_id,
                    company,
                    po.date_order or fields.Date.today()
                )
            wizard.pending_orders_amount = pending_amount

            current_amount = order.currency_id._convert(
                order.amount_total,
                company.currency_id,
                company,
                order.date_order or fields.Date.today()
            )
            wizard.current_order_amount = current_amount

            wizard.total_exposure = receivables + pending_amount + current_amount
            wizard.exceeded_amount = max(0.0, wizard.total_exposure - wizard.credit_limit)

    def _compute_is_manager(self):
        for wizard in self:
            wizard.is_manager = self.env.user.has_group('sales_team.group_sale_manager')

    def _format_monetary(self, amount):
        currency = self.currency_id or self.env.company.currency_id
        symbol = currency.symbol or ''
        if symbol:
            return f"{symbol} {amount:,.2f}"
        return f"{amount:,.2f}"

    def _get_overdue_amount(self, order):
        commercial_partner = order.partner_id.commercial_partner_id
        unpaid_invoices = self.env['account.move'].search([
            ('commercial_partner_id', '=', commercial_partner.id),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('move_type', '=', 'out_invoice'),
        ])
        overdue_amount = 0.0
        company = order.company_id or self.env.company
        for move in unpaid_invoices:
            if move.invoice_date_due and move.invoice_date_due < fields.Date.today():
                overdue_amount += move.currency_id._convert(
                    move.amount_residual,
                    company.currency_id,
                    company,
                    move.invoice_date or fields.Date.today()
                )
        return overdue_amount

    def action_request_approval(self):
        self.ensure_one()
        order = self.sale_order_id
        overdue_amount = self._get_overdue_amount(order)
        order_url = f"/web#id={order.id}&model=sale.order&view_type=form"

        body = Markup(
            '<div style="margin:0;padding:15px;background-color:#f1f8ff;border:1px solid #c8e1ff;'
            'border-radius:6px;font-family:sans-serif;font-size:13px;color:#24292e;">'
            '<p style="margin:0 0 10px 0;font-weight:bold;">'
            'Subject: Credit limit exceeded: {order_name}'
            '</p>'
            '<p style="margin:0 0 10px 0;">Hi {company_name},</p>'
            '<p style="margin:0 0 15px 0;">'
            'The Sales Order <strong>{order_name}</strong> needs your approval because '
            '<strong>Total amount is exceeding from credit limit.</strong>'
            '</p>'
            '<ul style="margin:0 0 15px 0;padding-left:20px;">'
            '<li style="margin-bottom:5px;">Customer: {customer}</li>'
            '<li style="margin-bottom:5px;">Credit Limit: {credit_limit}</li>'
            '<li style="margin-bottom:5px;">Unpaid Amount: {unpaid_amount}</li>'
            '<li style="margin-bottom:5px;">Overdue Amount: {overdue_amount}</li>'
            '<li style="margin-bottom:5px;">Order Amount: {order_amount}</li>'
            '<li style="margin-bottom:5px;color:#d93025;font-weight:bold;">'
            'Exceeded Credit: {exceeded_credit}'
            '</li>'
            '</ul>'
            '<div style="margin:15px 0;">'
            '<a href="{order_url}" style="background-color:#875A7B;padding:8px 16px;'
            'text-decoration:none;color:#fff;border-radius:5px;font-size:12px;'
            'font-weight:bold;display:inline-block;">View sales order</a>'
            '</div>'
            '<p style="margin:15px 0 0 0;">Thanks &amp; Regards,<br/>{salesperson}</p>'
            '</div>'
        ).format(
            order_name=order.name,
            company_name=order.company_id.name,
            customer=order.partner_id.name,
            credit_limit=self._format_monetary(self.credit_limit),
            unpaid_amount=self._format_monetary(self.total_receivables),
            overdue_amount=self._format_monetary(overdue_amount),
            order_amount=self._format_monetary(self.current_order_amount),
            exceeded_credit=self._format_monetary(self.exceeded_amount),
            order_url=order_url,
            salesperson=order.user_id.name or self.env.user.name,
        )

        order.message_post(
            body=body,
            subject=_("Credit limit exceeded: %s") % order.name,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )
        return {'type': 'ir.actions.act_window_close'}

    def action_confirm_order(self):
        self.ensure_one()
        if not self.env.user.has_group('sales_team.group_sale_manager'):
            raise UserError(_("Only sales managers are allowed to approve and confirm this order."))

        order = self.sale_order_id
        order.credit_limit_approved = True
        order.action_confirm()

        order_url = f"/web#id={order.id}&model=sale.order&view_type=form"
        body = Markup(
            '<div style="margin:0;padding:15px;background-color:#e6f4ea;border:1px solid #c2e7cd;'
            'border-radius:6px;font-family:sans-serif;font-size:13px;color:#24292e;">'
            '<p style="margin:0 0 10px 0;font-weight:bold;">'
            'Subject: Order Approved: {order_name}'
            '</p>'
            '<p style="margin:0 0 10px 0;">Hi {salesperson},</p>'
            '<p style="margin:0 0 15px 0;">'
            'The Sales Order <strong>{order_name}</strong> has been approved. '
            'You can proceed for further actions.'
            '</p>'
            '<div style="margin:15px 0;">'
            '<a href="{order_url}" style="background-color:#875A7B;padding:8px 16px;'
            'text-decoration:none;color:#fff;border-radius:5px;font-size:12px;'
            'font-weight:bold;display:inline-block;">View sales order</a>'
            '</div>'
            '<p style="margin:15px 0 0 0;">Thanks &amp; Regards,<br/>{company_name}</p>'
            '</div>'
        ).format(
            order_name=order.name,
            salesperson=order.user_id.name or '',
            order_url=order_url,
            company_name=order.company_id.name,
        )

        order.message_post(
            body=body,
            subject=_("Order Approved: %s") % order.name,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )
        return {'type': 'ir.actions.act_window_close'}

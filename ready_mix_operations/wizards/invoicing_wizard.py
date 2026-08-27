from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ReadyMixInvoicingWizard(models.TransientModel):
    _name = 'ready.mix.invoicing.wizard'
    _description = 'Ready Mix Invoicing Wizard'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    plant_id = fields.Many2one('ready.mix.plant', string='Plant')
    date_from = fields.Date(string='Date From', required=True,
                             default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date(string='Date To', required=True, default=fields.Date.today)
    grouping = fields.Selection([
        ('site', 'By Job Site'),
        ('order', 'By Sales Order'),
        ('day', 'By Day'),
        ('mix', 'By Mix Design'),
        ('single', 'Single Invoice'),
    ], string='Group By', default='site', required=True)
    journal_id = fields.Many2one('account.journal', string='Invoice Journal',
                                  domain=[('type', '=', 'sale')],
                                  default=lambda self: self.env['account.journal'].search(
                                      [('type', '=', 'sale')], limit=1))
    load_ids = fields.Many2many('ready.mix.load', string='Loads to Invoice',
                                 compute='_compute_load_ids')
    load_count = fields.Integer(compute='_compute_load_ids')
    total_volume = fields.Float(compute='_compute_load_ids', digits=(16, 2))
    total_amount = fields.Float(compute='_compute_load_ids', digits=(16, 4))

    @api.depends('partner_id', 'plant_id', 'date_from', 'date_to')
    def _compute_load_ids(self):
        for rec in self:
            domain = [
                ('partner_id', '=', rec.partner_id.id),
                ('state', '=', 'delivered'),
                ('invoiced', '=', False),
            ]
            if rec.date_from:
                domain.append(('delivery_date', '>=', rec.date_from))
            if rec.date_to:
                domain.append(('delivery_date', '<=', rec.date_to))
            if rec.plant_id:
                domain.append(('plant_id', '=', rec.plant_id.id))
            loads = self.env['ready.mix.load'].search(domain)
            rec.load_ids = loads
            rec.load_count = len(loads)
            rec.total_volume = sum(loads.mapped('volume_delivered'))
            rec.total_amount = sum(loads.mapped('subtotal'))

    def action_create_invoices(self):
        self.ensure_one()
        if not self.load_ids:
            raise UserError(_('No delivered, un-invoiced loads found for the selected criteria.'))

        invoices = self.env['account.move']

        if self.grouping == 'single':
            groups = {'all': self.load_ids}
        elif self.grouping == 'site':
            groups = {}
            for load in self.load_ids:
                key = load.jobsite_id.id or 'no_site'
                groups.setdefault(key, self.env['ready.mix.load'])
                groups[key] |= load
        elif self.grouping == 'order':
            groups = {}
            for load in self.load_ids:
                key = load.sale_order_id.id or 'no_order'
                groups.setdefault(key, self.env['ready.mix.load'])
                groups[key] |= load
        elif self.grouping == 'day':
            groups = {}
            for load in self.load_ids:
                key = str(load.delivery_date)
                groups.setdefault(key, self.env['ready.mix.load'])
                groups[key] |= load
        elif self.grouping == 'mix':
            groups = {}
            for load in self.load_ids:
                key = load.mix_product_id.id
                groups.setdefault(key, self.env['ready.mix.load'])
                groups[key] |= load
        else:
            groups = {'all': self.load_ids}

        for _key, loads in groups.items():
            invoice_lines = []
            for load in loads:
                product = load.mix_product_id.product_id
                if not product:
                    # Use a generic service product
                    product = self.env.ref('product.product_product_4', raise_if_not_found=False)
                invoice_lines.append((0, 0, {
                    'name': f'[{load.name}] {load.mix_product_id.name} - {load.delivery_date}',
                    'product_id': product.id if product else False,
                    'quantity': load.volume_delivered,
                    'price_unit': load.unit_price,
                }))

            invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': self.partner_id.id,
                'journal_id': self.journal_id.id,
                'invoice_line_ids': invoice_lines,
            })
            invoices |= invoice
            loads.write({'invoice_id': invoice.id})

        if len(invoices) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': invoices.id,
                'view_mode': 'form',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoices Created'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', invoices.ids)],
        }

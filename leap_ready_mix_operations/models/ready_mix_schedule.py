from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ReadyMixSchedule(models.Model):
    _name = 'ready.mix.schedule'
    _description = 'Delivery Schedule'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'delivery_date desc, name'

    name = fields.Char(string='Schedule Reference', required=True, copy=False,
                        default=lambda self: _('New'), tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True,
                                  tracking=True)
    jobsite_id = fields.Many2one('ready.mix.jobsite', string='Job Site',
                                  domain="[('partner_id','=',partner_id)]", tracking=True)
    plant_id = fields.Many2one('ready.mix.plant', string='Plant', required=True,
                                tracking=True)
    mix_product_id = fields.Many2one('ready.mix.product', string='Mix Design',
                                      required=True, tracking=True)
    sale_order_id = fields.Many2one('sale.order', string='Sales Order')
    delivery_date = fields.Date(string='Delivery Date', required=True, tracking=True)
    requested_volume = fields.Float(string='Requested Volume (m³)', required=True,
                                     digits=(16, 2), tracking=True)
    pour_rate = fields.Float(string='Pour Rate (m³/hr)', digits=(16, 2))
    start_time = fields.Float(string='Start Time', help='Decimal hours, e.g. 8.5 = 08:30')
    pump_required = fields.Boolean(string='Pump Required')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('dispatched', 'Dispatched'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    dispatch_ids = fields.One2many('ready.mix.dispatch', 'schedule_id', string='Dispatches')
    dispatch_count = fields.Integer(compute='_compute_dispatch_count')
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ready.mix.schedule') or _('New')
        return super().create(vals_list)

    def _compute_dispatch_count(self):
        for rec in self:
            rec.dispatch_count = len(rec.dispatch_ids)

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_generate_dispatches(self):
        """Auto-generate dispatch records based on volume and pour rate."""
        self.ensure_one()
        if not self.pour_rate:
            raise ValidationError(_('Pour rate is required to generate dispatches.'))
        # Calculate number of trucks needed (assuming 7m³ per truck)
        truck_capacity = 7.0
        num_trucks = int(self.requested_volume / truck_capacity) + (
            1 if self.requested_volume % truck_capacity else 0)
        interval_minutes = (truck_capacity / self.pour_rate) * 60 if self.pour_rate else 30
        for i in range(num_trucks):
            self.env['ready.mix.dispatch'].create({
                'schedule_id': self.id,
                'plant_id': self.plant_id.id,
                'partner_id': self.partner_id.id,
                'jobsite_id': self.jobsite_id.id,
                'mix_product_id': self.mix_product_id.id,
                'delivery_date': self.delivery_date,
                'sequence': i + 1,
                'volume': min(truck_capacity, self.requested_volume - i * truck_capacity),
                'planned_time': self.start_time + (i * interval_minutes / 60),
            })
        self.write({'state': 'dispatched'})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Dispatches',
            'res_model': 'ready.mix.dispatch',
            'view_mode': 'list,form',
            'domain': [('schedule_id', '=', self.id)],
        }

    def action_view_dispatches(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Dispatches',
            'res_model': 'ready.mix.dispatch',
            'view_mode': 'list,form',
            'domain': [('schedule_id', '=', self.id)],
            'context': {'default_schedule_id': self.id},
        }

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ReadyMixDispatch(models.Model):
    _name = 'ready.mix.dispatch'
    _description = 'Dispatch Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'delivery_date, planned_time, sequence'

    name = fields.Char(string='Dispatch Reference', required=True, copy=False,
                        default=lambda self: _('New'), tracking=True)
    schedule_id = fields.Many2one('ready.mix.schedule', string='Schedule', ondelete='set null')
    plant_id = fields.Many2one('ready.mix.plant', string='Plant', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    jobsite_id = fields.Many2one('ready.mix.jobsite', string='Job Site')
    mix_product_id = fields.Many2one('ready.mix.product', string='Mix Design', required=True)
    delivery_date = fields.Date(string='Delivery Date', required=True, tracking=True)
    sequence = fields.Integer(string='Truck No.', default=1)
    planned_time = fields.Float(string='Planned Time (hr)', help='e.g. 8.5 = 08:30')
    volume = fields.Float(string='Volume (m³)', required=True, digits=(16, 2))

    # Fleet
    vehicle_id = fields.Many2one('fleet.vehicle', string='Transit Mixer', tracking=True)
    driver_id = fields.Many2one('res.partner', string='Driver', tracking=True)
    pump_vehicle_id = fields.Many2one('fleet.vehicle', string='Pump', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('batching', 'Batching'),
        ('in_transit', 'In Transit'),
        ('discharging', 'Discharging'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    load_id = fields.Many2one('ready.mix.load', string='Load Ticket', readonly=True)
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ready.mix.dispatch') or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_batching(self):
        self.write({'state': 'batching'})

    def action_in_transit(self):
        self.write({'state': 'in_transit'})

    def action_discharging(self):
        self.write({'state': 'discharging'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_create_load(self):
        """Create a Load Ticket from this dispatch."""
        self.ensure_one()
        if self.load_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'ready.mix.load',
                'res_id': self.load_id.id,
                'view_mode': 'form',
            }
        load = self.env['ready.mix.load'].create({
            'dispatch_id': self.id,
            'plant_id': self.plant_id.id,
            'partner_id': self.partner_id.id,
            'jobsite_id': self.jobsite_id.id,
            'mix_product_id': self.mix_product_id.id,
            'vehicle_id': self.vehicle_id.id,
            'driver_id': self.driver_id.id,
            'pump_vehicle_id': self.pump_vehicle_id.id,
            'volume_ordered': self.volume,
            'delivery_date': self.delivery_date,
        })
        self.write({'load_id': load.id, 'state': 'batching'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ready.mix.load',
            'res_id': load.id,
            'view_mode': 'form',
        }

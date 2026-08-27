from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ReadyMixPlant(models.Model):
    _name = 'ready.mix.plant'
    _description = 'Ready Mix Plant'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Plant Name', required=True, tracking=True)
    code = fields.Char(string='Plant Code', required=True, tracking=True)
    active = fields.Boolean(default=True)
    partner_id = fields.Many2one('res.partner', string='Address')
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    timezone = fields.Selection(
        string='Timezone',
        selection='_tz_get',
        default='UTC',
    )
    capacity_m3_per_hour = fields.Float(string='Capacity (m³/hr)', default=60.0)
    max_trucks = fields.Integer(string='Max Simultaneous Trucks', default=10)

    # Compliance profile
    quality_standard = fields.Selection([
        ('en206', 'EN 206'),
        ('aci318', 'ACI 318 / ASTM C94'),
        ('is456', 'IS 456'),
    ], string='Quality Standard', default='en206', required=True, tracking=True)
    block_on_cert_gap = fields.Boolean(string='Block Dispatch on Expired Certificate', default=True)
    block_on_stock_gap = fields.Boolean(string='Block Dispatch on Low Stock', default=False)
    max_transit_time = fields.Integer(string='Max Transit Time (min)', default=90)
    max_drum_revolutions = fields.Integer(string='Max Drum Revolutions', default=300)

    # Cost rates
    transport_rate = fields.Float(string='Transport Rate (per m³)', digits=(16, 4))
    driver_rate = fields.Float(string='Driver Rate (per hour)', digits=(16, 4))
    pump_rate = fields.Float(string='Pump Rate (per m³)', digits=(16, 4))
    overhead_rate = fields.Float(string='Overhead Rate (per m³)', digits=(16, 4))

    silo_ids = fields.One2many('ready.mix.silo', 'plant_id', string='Silos / Storage')
    silo_count = fields.Integer(compute='_compute_counts', string='Silos')
    load_count = fields.Integer(compute='_compute_counts', string='Loads')

    @api.model
    def _tz_get(self):
        import pytz
        return [(tz, tz) for tz in sorted(pytz.all_timezones)]

    def _compute_counts(self):
        for rec in self:
            rec.silo_count = len(rec.silo_ids)
            rec.load_count = self.env['ready.mix.load'].search_count([('plant_id', '=', rec.id)])

    @api.constrains('code')
    def _check_code_unique(self):
        for rec in self:
            if self.search_count([('code', '=', rec.code), ('id', '!=', rec.id)]) > 0:
                raise ValidationError(_('Plant code must be unique.'))

    def action_view_silos(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Silos',
            'res_model': 'ready.mix.silo',
            'view_mode': 'list,form',
            'domain': [('plant_id', '=', self.id)],
            'context': {'default_plant_id': self.id},
        }

    def action_view_loads(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Load Tickets',
            'res_model': 'ready.mix.load',
            'view_mode': 'list,form',
            'domain': [('plant_id', '=', self.id)],
            'context': {'default_plant_id': self.id},
        }

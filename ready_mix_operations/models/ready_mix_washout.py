from odoo import models, fields, api, _


class ReadyMixWashout(models.Model):
    _name = 'ready.mix.washout'
    _description = 'Washout Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'washout_date desc, name'

    name = fields.Char(string='Washout Reference', required=True, copy=False,
                        default=lambda self: _('New'), tracking=True)
    plant_id = fields.Many2one('ready.mix.plant', string='Plant', required=True, tracking=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Transit Mixer', tracking=True)
    driver_id = fields.Many2one('res.partner', string='Driver')
    washout_date = fields.Date(string='Date', required=True, default=fields.Date.today,
                                tracking=True)
    washout_time = fields.Float(string='Time (hr)', help='Decimal hours e.g. 14.5 = 14:30')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    load_id = fields.Many2one('ready.mix.load', string='Last Load Ticket')
    returned_volume = fields.Float(string='Returned Concrete (m³)', digits=(16, 2))
    washout_water_vol = fields.Float(string='Washout Water Used (L)', digits=(16, 2))
    waste_disposal_method = fields.Selection([
        ('reclaim', 'Reclaim Plant'),
        ('hardstand', 'Hardstand Area'),
        ('offsite', 'Off-site Disposal'),
        ('other', 'Other'),
    ], string='Disposal Method', default='reclaim')
    environmental_notes = fields.Text(string='Environmental Notes')
    operator_id = fields.Many2one('res.users', string='Operator', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], default='draft', string='Status', tracking=True)
    notes = fields.Text(string='Remarks')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ready.mix.washout') or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        self.write({'state': 'confirmed'})

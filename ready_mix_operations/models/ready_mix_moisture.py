from odoo import models, fields, api, _


class ReadyMixMoistureLog(models.Model):
    _name = 'ready.mix.moisture'
    _description = 'Aggregate Moisture Log'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'log_date desc, plant_id'

    name = fields.Char(string='Reference', required=True, copy=False,
                        default=lambda self: _('New'), tracking=True)
    plant_id = fields.Many2one('ready.mix.plant', string='Plant', required=True, tracking=True)
    log_date = fields.Date(string='Date', required=True, default=fields.Date.today, tracking=True)
    technician_id = fields.Many2one('res.users', string='Technician')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    line_ids = fields.One2many('ready.mix.moisture.line', 'moisture_id', string='Readings')
    notes = fields.Text(string='Notes')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], default='draft', string='Status', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ready.mix.moisture') or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        self.write({'state': 'confirmed'})


class ReadyMixMoistureLine(models.Model):
    _name = 'ready.mix.moisture.line'
    _description = 'Moisture Log Line'
    _order = 'sequence, id'

    moisture_id = fields.Many2one('ready.mix.moisture', string='Log', required=True,
                                   ondelete='cascade')
    sequence = fields.Integer(default=10)
    product_id = fields.Many2one('product.product', string='Aggregate', required=True)
    silo_id = fields.Many2one('ready.mix.silo', string='Silo / Bin')
    moisture_pct = fields.Float(string='Moisture Content (%)', required=True, digits=(16, 2))
    absorption_pct = fields.Float(string='Absorption (%)', digits=(16, 2))
    free_moisture = fields.Float(string='Free Moisture (%)', compute='_compute_free', store=True,
                                  digits=(16, 2))
    notes = fields.Char(string='Remarks')

    @api.depends('moisture_pct', 'absorption_pct')
    def _compute_free(self):
        for rec in self:
            rec.free_moisture = rec.moisture_pct - rec.absorption_pct

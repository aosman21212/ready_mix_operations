from odoo import models, fields, api, _


class ReadyMixJobSite(models.Model):
    _name = 'ready.mix.jobsite'
    _description = 'Customer Job Site'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Site Name', required=True, tracking=True)
    code = fields.Char(string='Site Code')
    partner_id = fields.Many2one('res.partner', string='Customer', required=True,
                                  tracking=True, ondelete='restrict')
    active = fields.Boolean(default=True)

    # Location
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street2')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State')
    country_id = fields.Many2one('res.country', string='Country')
    zip = fields.Char(string='ZIP')
    distance_km = fields.Float(string='Distance from Plant (km)', digits=(16, 2))

    # Site contacts
    site_engineer = fields.Char(string='Site Engineer')
    site_phone = fields.Char(string='Site Phone')
    site_email = fields.Char(string='Site Email')

    # Requirements
    pump_required = fields.Boolean(string='Pump Required', default=False)
    notes = fields.Text(string='Special Requirements')

    # Related
    rate_agreement_ids = fields.One2many('ready.mix.rate.agreement', 'jobsite_id',
                                          string='Rate Agreements')
    load_ids = fields.One2many('ready.mix.load', 'jobsite_id', string='Loads')
    load_count = fields.Integer(compute='_compute_load_count', string='Total Loads')

    def _compute_load_count(self):
        for rec in self:
            rec.load_count = len(rec.load_ids)

    def action_view_loads(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Loads',
            'res_model': 'ready.mix.load',
            'view_mode': 'list,form',
            'domain': [('jobsite_id', '=', self.id)],
            'context': {'default_jobsite_id': self.id},
        }

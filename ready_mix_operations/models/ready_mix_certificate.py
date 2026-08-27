from odoo import models, fields, api, _


class ReadyMixCertificate(models.Model):
    _name = 'ready.mix.certificate'
    _description = 'Certification Register'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'expiry_date, name'

    name = fields.Char(string='Certificate Name', required=True, tracking=True)
    cert_type = fields.Selection([
        ('plant', 'Plant Certificate'),
        ('personnel', 'Personnel Certificate'),
        ('vehicle', 'Vehicle Certificate'),
        ('material', 'Material Certificate'),
        ('other', 'Other'),
    ], string='Type', required=True, default='plant', tracking=True)
    plant_id = fields.Many2one('ready.mix.plant', string='Plant', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Holder / Supplier')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    employee_id = fields.Many2one('res.partner', string='Personnel')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    reference_no = fields.Char(string='Certificate No.')
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date', required=True, tracking=True)
    issuing_body = fields.Char(string='Issuing Authority')
    scope = fields.Char(string='Scope / Description')

    status = fields.Selection([
        ('valid', 'Valid'),
        ('expiring_soon', 'Expiring Soon'),
        ('expired', 'Expired'),
    ], string='Status', compute='_compute_status', store=True, tracking=True)

    attachment_ids = fields.Many2many('ir.attachment', string='Documents')
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    @api.depends('expiry_date')
    def _compute_status(self):
        today = fields.Date.today()
        for rec in self:
            if not rec.expiry_date:
                rec.status = 'valid'
                continue
            days = (rec.expiry_date - today).days
            if days < 0:
                rec.status = 'expired'
            elif days <= 30:
                rec.status = 'expiring_soon'
            else:
                rec.status = 'valid'

    def action_renew(self):
        """Open a form to create a renewal."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ready.mix.certificate',
            'view_mode': 'form',
            'context': {
                'default_name': self.name,
                'default_cert_type': self.cert_type,
                'default_plant_id': self.plant_id.id,
                'default_partner_id': self.partner_id.id,
                'default_vehicle_id': self.vehicle_id.id,
                'default_issuing_body': self.issuing_body,
                'default_scope': self.scope,
            },
        }

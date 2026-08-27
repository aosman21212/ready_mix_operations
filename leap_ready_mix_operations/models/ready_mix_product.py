from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ReadyMixProduct(models.Model):
    _name = 'ready.mix.product'
    _description = 'Concrete Mix Design'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Mix Design Name', required=True, tracking=True)
    code = fields.Char(string='Mix Code', required=True, tracking=True)
    product_id = fields.Many2one('product.product', string='Linked Saleable Product',
                                  domain=[('type', '=', 'service')])
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    # Specification
    grade = fields.Char(string='Concrete Grade', help='e.g. C30/37, M30, 4000 psi')
    compressive_strength = fields.Float(string='Target Strength (MPa)', digits=(16, 2))
    slump_min = fields.Float(string='Slump Min (mm)', digits=(16, 1))
    slump_max = fields.Float(string='Slump Max (mm)', digits=(16, 1))
    max_wc_ratio = fields.Float(string='Max W/C Ratio', digits=(16, 3))
    cement_content = fields.Float(string='Min Cement Content (kg/m³)', digits=(16, 2))
    max_aggregate_size = fields.Float(string='Max Aggregate Size (mm)', digits=(16, 1))
    air_content_min = fields.Float(string='Air Content Min (%)', digits=(16, 2))
    air_content_max = fields.Float(string='Air Content Max (%)', digits=(16, 2))
    exposure_class = fields.Char(string='Exposure Class')

    # Approval
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('archived', 'Archived'),
    ], string='Status', default='draft', tracking=True)
    approved_by = fields.Many2one('res.users', string='Approved By', tracking=True)
    approval_date = fields.Date(string='Approval Date')
    consultant_approved = fields.Boolean(string='Consultant Approved', tracking=True)
    consultant_name = fields.Char(string='Consultant Name')
    consultant_date = fields.Date(string='Consultant Approval Date')

    recipe_line_ids = fields.One2many('ready.mix.product.line', 'mix_id', string='Recipe Lines')
    notes = fields.Text(string='Technical Notes')

    @api.constrains('slump_min', 'slump_max')
    def _check_slump(self):
        for rec in self:
            if rec.slump_min and rec.slump_max and rec.slump_min > rec.slump_max:
                raise ValidationError(_('Slump Min cannot be greater than Slump Max.'))

    def action_approve(self):
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approval_date': fields.Date.today(),
        })

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_archive(self):
        self.write({'state': 'archived', 'active': False})


class ReadyMixProductLine(models.Model):
    _name = 'ready.mix.product.line'
    _description = 'Mix Design Recipe Line'
    _order = 'sequence, id'

    mix_id = fields.Many2one('ready.mix.product', string='Mix Design',
                              required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    product_id = fields.Many2one('product.product', string='Material', required=True)
    silo_id = fields.Many2one('ready.mix.silo', string='Silo / Source')
    quantity = fields.Float(string='Quantity (kg/m³)', required=True, digits=(16, 3))
    uom_id = fields.Many2one('uom.uom', string='UoM',
                              default=lambda self: self.env.ref('uom.product_uom_kgm'))
    moisture_correction = fields.Boolean(string='Apply Moisture Correction', default=False)
    notes = fields.Char(string='Notes')

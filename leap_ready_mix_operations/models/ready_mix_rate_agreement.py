from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ReadyMixRateAgreement(models.Model):
    _name = 'ready.mix.rate.agreement'
    _description = 'Rate Agreement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'partner_id, jobsite_id, name'

    name = fields.Char(string='Agreement Reference', required=True, tracking=True,
                        copy=False, default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', string='Customer', required=True,
                                  tracking=True, ondelete='restrict')
    jobsite_id = fields.Many2one('ready.mix.jobsite', string='Job Site',
                                  domain="[('partner_id','=',partner_id)]", tracking=True)
    plant_id = fields.Many2one('ready.mix.plant', string='Plant', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    date_from = fields.Date(string='Valid From', required=True)
    date_to = fields.Date(string='Valid To', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)
    pricelist_line_ids = fields.One2many('ready.mix.rate.line', 'agreement_id',
                                          string='Price Lines')
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ready.mix.rate.agreement') or _('New')
        return super().create(vals_list)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise ValidationError(_('Valid From date cannot be after Valid To date.'))

    def action_activate(self):
        self.write({'state': 'active'})

    def action_expire(self):
        self.write({'state': 'expired'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def get_price(self, mix_product_id):
        """Return unit price for the given mix product, if a matching line exists."""
        self.ensure_one()
        line = self.pricelist_line_ids.filtered(
            lambda l: l.mix_product_id.id == mix_product_id
        )
        return line[:1].unit_price if line else 0.0


class ReadyMixRateLine(models.Model):
    _name = 'ready.mix.rate.line'
    _description = 'Rate Agreement Line'
    _order = 'sequence, id'

    agreement_id = fields.Many2one('ready.mix.rate.agreement', string='Agreement',
                                    required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    mix_product_id = fields.Many2one('ready.mix.product', string='Mix Design', required=True)
    unit_price = fields.Float(string='Unit Price', required=True, digits=(16, 4))
    currency_id = fields.Many2one(related='agreement_id.currency_id')
    notes = fields.Char(string='Notes')

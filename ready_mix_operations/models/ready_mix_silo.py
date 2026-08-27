from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ReadyMixSilo(models.Model):
    _name = 'ready.mix.silo'
    _description = 'Silo / Storage Asset'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'plant_id, name'

    name = fields.Char(string='Silo / Tank Name', required=True, tracking=True)
    plant_id = fields.Many2one('ready.mix.plant', string='Plant', required=True,
                                ondelete='cascade', tracking=True)
    silo_type = fields.Selection([
        ('cement', 'Cement Silo'),
        ('aggregate', 'Aggregate Bin'),
        ('water', 'Water Tank'),
        ('admixture', 'Admixture Tank'),
        ('other', 'Other'),
    ], string='Type', required=True, default='cement', tracking=True)
    product_id = fields.Many2one('product.product', string='Material Stored')
    capacity_tonnes = fields.Float(string='Capacity (tonnes)', digits=(16, 2))
    current_stock = fields.Float(string='Current Stock (tonnes)', digits=(16, 2), tracking=True)
    reorder_point = fields.Float(string='Reorder Point (tonnes)', digits=(16, 2))
    fill_percentage = fields.Float(string='Fill %', compute='_compute_fill_percentage', store=True)
    active = fields.Boolean(default=True)

    # Calibration
    last_calibration_date = fields.Date(string='Last Calibration Date')
    calibration_due_date = fields.Date(string='Calibration Due Date')
    calibration_status = fields.Selection([
        ('valid', 'Valid'),
        ('due_soon', 'Due Soon'),
        ('overdue', 'Overdue'),
        ('not_set', 'Not Set'),
    ], string='Calibration Status', compute='_compute_calibration_status', store=True)

    notes = fields.Text(string='Notes')

    @api.depends('current_stock', 'capacity_tonnes')
    def _compute_fill_percentage(self):
        for rec in self:
            if rec.capacity_tonnes:
                rec.fill_percentage = (rec.current_stock / rec.capacity_tonnes) * 100
            else:
                rec.fill_percentage = 0.0

    @api.depends('calibration_due_date')
    def _compute_calibration_status(self):
        today = fields.Date.today()
        for rec in self:
            if not rec.calibration_due_date:
                rec.calibration_status = 'not_set'
            elif rec.calibration_due_date < today:
                rec.calibration_status = 'overdue'
            elif (rec.calibration_due_date - today).days <= 30:
                rec.calibration_status = 'due_soon'
            else:
                rec.calibration_status = 'valid'

    @api.constrains('current_stock', 'capacity_tonnes')
    def _check_stock(self):
        for rec in self:
            if rec.current_stock < 0:
                raise ValidationError(_('Stock cannot be negative for silo %s.') % rec.name)
            if rec.capacity_tonnes and rec.current_stock > rec.capacity_tonnes:
                raise ValidationError(
                    _('Stock cannot exceed capacity for silo %s.') % rec.name)

    def is_below_reorder(self):
        self.ensure_one()
        return self.current_stock <= self.reorder_point

from odoo import models, fields, api, _


class ReadyMixCostSheet(models.Model):
    _name = 'ready.mix.cost.sheet'
    _description = 'Load Cost Sheet'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Cost Sheet Ref', required=True, copy=False,
                        default=lambda self: _('New'), tracking=True)
    load_id = fields.Many2one('ready.mix.load', string='Load Ticket', required=True,
                               ondelete='cascade')
    plant_id = fields.Many2one(related='load_id.plant_id', store=True)
    partner_id = fields.Many2one(related='load_id.partner_id', store=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency',
                                   default=lambda self: self.env.company.currency_id)

    volume = fields.Float(related='load_id.volume_delivered', string='Volume (m³)', digits=(16, 2))

    # Costs
    material_cost = fields.Float(string='Material Cost', digits=(16, 4),
                                  compute='_compute_material_cost', store=True)
    transport_cost = fields.Float(string='Transport Cost', digits=(16, 4))
    driver_cost = fields.Float(string='Driver Cost', digits=(16, 4))
    pump_cost = fields.Float(string='Pump Cost', digits=(16, 4))
    overhead_cost = fields.Float(string='Overhead Cost', digits=(16, 4))
    other_cost = fields.Float(string='Other Cost', digits=(16, 4))

    total_cost = fields.Float(string='Total Cost', compute='_compute_totals', store=True,
                               digits=(16, 4))
    cost_per_m3 = fields.Float(string='Cost per m³', compute='_compute_totals', store=True,
                                digits=(16, 4))
    revenue = fields.Float(related='load_id.subtotal', string='Revenue', digits=(16, 4))
    margin = fields.Float(string='Margin', compute='_compute_totals', store=True, digits=(16, 4))
    margin_pct = fields.Float(string='Margin %', compute='_compute_totals', store=True,
                               digits=(16, 2))

    # Lock margin on invoice post
    margin_locked = fields.Boolean(string='Margin Locked', default=False)

    cost_line_ids = fields.One2many('ready.mix.cost.line', 'cost_sheet_id', string='Cost Lines')
    notes = fields.Text(string='Notes')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], default='draft', string='Status', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ready.mix.cost') or _('New')
        return super().create(vals_list)

    @api.depends('load_id.material_line_ids', 'load_id.material_line_ids.actual_qty')
    def _compute_material_cost(self):
        for rec in self:
            total = 0.0
            for line in rec.load_id.material_line_ids:
                cost = line.product_id.standard_price or 0.0
                total += (line.actual_qty / 1000) * cost  # kg → tonnes
            rec.material_cost = total

    @api.depends('material_cost', 'transport_cost', 'driver_cost', 'pump_cost',
                 'overhead_cost', 'other_cost', 'revenue', 'volume')
    def _compute_totals(self):
        for rec in self:
            total = (rec.material_cost + rec.transport_cost + rec.driver_cost +
                     rec.pump_cost + rec.overhead_cost + rec.other_cost)
            rec.total_cost = total
            rec.cost_per_m3 = total / rec.volume if rec.volume else 0.0
            margin = rec.revenue - total
            rec.margin = margin
            rec.margin_pct = (margin / rec.revenue * 100) if rec.revenue else 0.0

    def action_compute_from_plant(self):
        """Fill cost fields from plant rates."""
        for rec in self:
            plant = rec.load_id.plant_id
            vol = rec.volume
            if plant and vol:
                rec.transport_cost = plant.transport_rate * vol
                rec.overhead_cost = plant.overhead_rate * vol
                rec.pump_cost = plant.pump_rate * vol if rec.load_id.pump_vehicle_id else 0.0
                # Driver cost from discharge duration
                hours = rec.load_id.discharge_duration / 60 if rec.load_id.discharge_duration else 0
                rec.driver_cost = plant.driver_rate * hours

    def action_confirm(self):
        self.write({'state': 'confirmed'})


class ReadyMixCostLine(models.Model):
    _name = 'ready.mix.cost.line'
    _description = 'Cost Sheet Line'
    _order = 'sequence, id'

    cost_sheet_id = fields.Many2one('ready.mix.cost.sheet', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    description = fields.Char(string='Description', required=True)
    cost_type = fields.Selection([
        ('material', 'Material'),
        ('transport', 'Transport'),
        ('driver', 'Driver'),
        ('pump', 'Pump'),
        ('overhead', 'Overhead'),
        ('other', 'Other'),
    ], string='Type', required=True, default='other')
    quantity = fields.Float(string='Qty', digits=(16, 3))
    unit = fields.Char(string='Unit')
    unit_cost = fields.Float(string='Unit Cost', digits=(16, 4))
    subtotal = fields.Float(string='Subtotal', compute='_compute_subtotal', store=True,
                             digits=(16, 4))

    @api.depends('quantity', 'unit_cost')
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.quantity * rec.unit_cost

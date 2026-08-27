from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ReadyMixLoad(models.Model):
    _name = 'ready.mix.load'
    _description = 'Load Ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'delivery_date desc, name'

    name = fields.Char(string='Ticket No.', required=True, copy=False,
                        default=lambda self: _('New'), tracking=True)
    dispatch_id = fields.Many2one('ready.mix.dispatch', string='Dispatch')
    schedule_id = fields.Many2one(related='dispatch_id.schedule_id', string='Schedule', store=True)
    sale_order_id = fields.Many2one('sale.order', string='Sales Order')

    # Parties
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    jobsite_id = fields.Many2one('ready.mix.jobsite', string='Job Site',
                                  domain="[('partner_id','=',partner_id)]", tracking=True)
    plant_id = fields.Many2one('ready.mix.plant', string='Plant', required=True, tracking=True)
    mix_product_id = fields.Many2one('ready.mix.product', string='Mix Design',
                                      required=True, tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    # Fleet
    vehicle_id = fields.Many2one('fleet.vehicle', string='Transit Mixer', tracking=True)
    driver_id = fields.Many2one('res.partner', string='Driver', tracking=True)
    pump_vehicle_id = fields.Many2one('fleet.vehicle', string='Pump Truck')
    pump_operator_id = fields.Many2one('res.partner', string='Pump Operator')

    # Volume
    delivery_date = fields.Date(string='Delivery Date', required=True, default=fields.Date.today,
                                 tracking=True)
    volume_ordered = fields.Float(string='Volume Ordered (m³)', digits=(16, 2), tracking=True)
    volume_delivered = fields.Float(string='Volume Delivered (m³)', digits=(16, 2), tracking=True)
    volume_returned = fields.Float(string='Volume Returned (m³)', digits=(16, 2))

    # Timeline
    batching_time = fields.Datetime(string='Batching Time', tracking=True)
    departure_time = fields.Datetime(string='Departure Time')
    arrival_time = fields.Datetime(string='Arrival Time')
    discharge_start_time = fields.Datetime(string='Discharge Start')
    discharge_end_time = fields.Datetime(string='Discharge End')
    return_time = fields.Datetime(string='Return Time')

    # Computed times
    transit_duration = fields.Float(string='Transit (min)', compute='_compute_durations', store=True)
    waiting_duration = fields.Float(string='Waiting (min)', compute='_compute_durations', store=True)
    discharge_duration = fields.Float(string='Discharge (min)', compute='_compute_durations', store=True)

    # Drum
    drum_revolutions = fields.Integer(string='Drum Revolutions', tracking=True)
    water_added_site = fields.Float(string='Water Added at Site (L)', digits=(16, 2))

    # Compliance
    wc_ratio_actual = fields.Float(string='Actual W/C Ratio', digits=(16, 3))
    compliance_breach = fields.Boolean(string='Compliance Breach', compute='_compute_compliance', store=True)
    compliance_notes = fields.Text(string='Compliance Notes')

    # Material consumption lines
    material_line_ids = fields.One2many('ready.mix.load.material', 'load_id',
                                         string='Material Consumption')

    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('batching', 'Batching'),
        ('in_transit', 'In Transit'),
        ('discharging', 'Discharging'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    # Invoicing
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    invoiced = fields.Boolean(string='Invoiced', compute='_compute_invoiced', store=True)
    unit_price = fields.Float(string='Unit Price', digits=(16, 4))
    subtotal = fields.Float(string='Subtotal', compute='_compute_subtotal', store=True)

    # QC links
    qc_test_ids = fields.One2many('ready.mix.qc.test', 'load_id', string='QC Tests')
    sample_ids = fields.One2many('ready.mix.sample', 'load_id', string='Specimens')
    qc_test_count = fields.Integer(compute='_compute_qc_counts')
    sample_count = fields.Integer(compute='_compute_qc_counts')
    cost_sheet_id = fields.Many2one('ready.mix.cost.sheet', string='Cost Sheet')
    ncr_ids = fields.One2many('ready.mix.ncr', 'load_id', string='NCRs')
    ncr_count = fields.Integer(compute='_compute_ncr_count')

    # Signature
    signed_by = fields.Char(string='Signed By (Site)')
    signed_time = fields.Datetime(string='Signature Time')

    notes = fields.Text(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ready.mix.load') or _('New')
        return super().create(vals_list)

    @api.depends('departure_time', 'arrival_time', 'arrival_time', 'discharge_start_time',
                 'discharge_start_time', 'discharge_end_time')
    def _compute_durations(self):
        for rec in self:
            if rec.departure_time and rec.arrival_time:
                diff = rec.arrival_time - rec.departure_time
                rec.transit_duration = diff.total_seconds() / 60
            else:
                rec.transit_duration = 0.0
            if rec.arrival_time and rec.discharge_start_time:
                diff = rec.discharge_start_time - rec.arrival_time
                rec.waiting_duration = diff.total_seconds() / 60
            else:
                rec.waiting_duration = 0.0
            if rec.discharge_start_time and rec.discharge_end_time:
                diff = rec.discharge_end_time - rec.discharge_start_time
                rec.discharge_duration = diff.total_seconds() / 60
            else:
                rec.discharge_duration = 0.0

    @api.depends('drum_revolutions', 'transit_duration', 'wc_ratio_actual',
                 'mix_product_id', 'plant_id')
    def _compute_compliance(self):
        for rec in self:
            breach = False
            notes = []
            plant = rec.plant_id
            if plant:
                if plant.max_drum_revolutions and rec.drum_revolutions > plant.max_drum_revolutions:
                    breach = True
                    notes.append(_('Drum revolutions exceeded limit (%d > %d).') % (
                        rec.drum_revolutions, plant.max_drum_revolutions))
                if plant.max_transit_time and rec.transit_duration > plant.max_transit_time:
                    breach = True
                    notes.append(_('Transit time exceeded limit (%.0f > %d min).') % (
                        rec.transit_duration, plant.max_transit_time))
            mix = rec.mix_product_id
            if mix and mix.max_wc_ratio and rec.wc_ratio_actual > mix.max_wc_ratio:
                breach = True
                notes.append(_('W/C ratio exceeded max (%.3f > %.3f).') % (
                    rec.wc_ratio_actual, mix.max_wc_ratio))
            rec.compliance_breach = breach
            rec.compliance_notes = '\n'.join(notes)

    @api.depends('invoice_id', 'invoice_id.state')
    def _compute_invoiced(self):
        for rec in self:
            rec.invoiced = bool(rec.invoice_id and rec.invoice_id.state != 'cancel')

    @api.depends('volume_delivered', 'unit_price')
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.volume_delivered * rec.unit_price

    def _compute_qc_counts(self):
        for rec in self:
            rec.qc_test_count = len(rec.qc_test_ids)
            rec.sample_count = len(rec.sample_ids)

    def _compute_ncr_count(self):
        for rec in self:
            rec.ncr_count = len(rec.ncr_ids)

    # --- State transitions ---
    def action_batching(self):
        self.write({'state': 'batching', 'batching_time': fields.Datetime.now()})

    def action_in_transit(self):
        self.write({'state': 'in_transit', 'departure_time': fields.Datetime.now()})

    def action_discharging(self):
        self.write({'state': 'discharging', 'discharge_start_time': fields.Datetime.now()})

    def action_delivered(self):
        vals = {'state': 'delivered', 'discharge_end_time': fields.Datetime.now()}
        if not self.volume_delivered:
            vals['volume_delivered'] = self.volume_ordered
        self.write(vals)
        # Auto-generate QC samples if mix design specifies
        self._auto_create_samples()

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def _auto_create_samples(self):
        """Create cube/cylinder specimen records automatically."""
        for rec in self:
            if rec.sample_count == 0:
                for days in [7, 28]:
                    self.env['ready.mix.sample'].create({
                        'load_id': rec.id,
                        'plant_id': rec.plant_id.id,
                        'partner_id': rec.partner_id.id,
                        'mix_product_id': rec.mix_product_id.id,
                        'sample_date': rec.delivery_date,
                        'test_age_days': days,
                        'test_due_date': fields.Date.from_string(rec.delivery_date) +
                                         __import__('datetime').timedelta(days=days)
                        if rec.delivery_date else False,
                    })

    # --- Smart buttons ---
    def action_view_qc_tests(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'QC Tests',
            'res_model': 'ready.mix.qc.test',
            'view_mode': 'list,form',
            'domain': [('load_id', '=', self.id)],
            'context': {'default_load_id': self.id},
        }

    def action_view_samples(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Specimens',
            'res_model': 'ready.mix.sample',
            'view_mode': 'list,form',
            'domain': [('load_id', '=', self.id)],
            'context': {'default_load_id': self.id},
        }

    def action_view_ncrs(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'NCRs',
            'res_model': 'ready.mix.ncr',
            'view_mode': 'list,form',
            'domain': [('load_id', '=', self.id)],
            'context': {'default_load_id': self.id},
        }

    def action_create_cost_sheet(self):
        self.ensure_one()
        if self.cost_sheet_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'ready.mix.cost.sheet',
                'res_id': self.cost_sheet_id.id,
                'view_mode': 'form',
            }
        cost = self.env['ready.mix.cost.sheet'].create({'load_id': self.id})
        self.cost_sheet_id = cost.id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ready.mix.cost.sheet',
            'res_id': cost.id,
            'view_mode': 'form',
        }

    def _compute_access_url(self):
        for rec in self:
            rec.access_url = '/my/loads/%s' % rec.id


class ReadyMixLoadMaterial(models.Model):
    _name = 'ready.mix.load.material'
    _description = 'Load Material Consumption'
    _order = 'sequence, id'

    load_id = fields.Many2one('ready.mix.load', string='Load', required=True,
                               ondelete='cascade')
    sequence = fields.Integer(default=10)
    product_id = fields.Many2one('product.product', string='Material', required=True)
    silo_id = fields.Many2one('ready.mix.silo', string='Silo / Source')
    target_qty = fields.Float(string='Target (kg)', digits=(16, 3))
    actual_qty = fields.Float(string='Actual (kg)', digits=(16, 3))
    moisture_pct = fields.Float(string='Moisture %', digits=(16, 2))
    moisture_corrected_qty = fields.Float(string='Corrected Qty (kg)',
                                           compute='_compute_corrected', store=True)
    variance = fields.Float(string='Variance (kg)', compute='_compute_variance', store=True)

    @api.depends('actual_qty', 'moisture_pct')
    def _compute_corrected(self):
        for rec in self:
            if rec.moisture_pct:
                rec.moisture_corrected_qty = rec.actual_qty / (1 + rec.moisture_pct / 100)
            else:
                rec.moisture_corrected_qty = rec.actual_qty

    @api.depends('target_qty', 'actual_qty')
    def _compute_variance(self):
        for rec in self:
            rec.variance = rec.actual_qty - rec.target_qty

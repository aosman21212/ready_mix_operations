from odoo import models, fields, api, _


class ReadyMixSample(models.Model):
    _name = 'ready.mix.sample'
    _description = 'Cube / Cylinder Specimen'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'test_due_date, name'

    name = fields.Char(string='Specimen Reference', required=True, copy=False,
                        default=lambda self: _('New'), tracking=True)
    load_id = fields.Many2one('ready.mix.load', string='Load Ticket', required=True,
                               ondelete='cascade', tracking=True)
    plant_id = fields.Many2one(related='load_id.plant_id', store=True)
    partner_id = fields.Many2one(related='load_id.partner_id', store=True)
    mix_product_id = fields.Many2one(related='load_id.mix_product_id', store=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    sample_type = fields.Selection([
        ('cube', '150mm Cube'),
        ('cylinder', '150x300 Cylinder'),
        ('beam', 'Beam'),
    ], string='Specimen Type', default='cube', required=True)
    sample_date = fields.Date(string='Casting Date', required=True, default=fields.Date.today)
    test_age_days = fields.Integer(string='Test Age (days)', default=28)
    test_due_date = fields.Date(string='Test Due Date', tracking=True)
    test_date = fields.Date(string='Actual Test Date')
    technician_id = fields.Many2one('res.users', string='QC Technician')

    # Results
    failure_load_kn = fields.Float(string='Failure Load (kN)', digits=(16, 2))
    cross_section_area = fields.Float(string='Cross-Section (mm²)', digits=(16, 2),
                                       default=22500.0)  # 150x150
    compressive_strength = fields.Float(string='Compressive Strength (MPa)',
                                         compute='_compute_strength', store=True, digits=(16, 2))
    target_strength = fields.Float(related='mix_product_id.compressive_strength',
                                    string='Target Strength (MPa)', digits=(16, 2))
    result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('pending', 'Pending'),
    ], string='Result', compute='_compute_result', store=True, tracking=True)

    state = fields.Selection([
        ('pending', 'Pending'),
        ('tested', 'Tested'),
        ('certified', 'Certified'),
    ], string='Status', default='pending', tracking=True)
    ncr_id = fields.Many2one('ready.mix.ncr', string='Linked NCR')
    certificate_issued = fields.Boolean(string='Certificate Issued', default=False)
    notes = fields.Text(string='Remarks')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ready.mix.sample') or _('New')
        return super().create(vals_list)

    @api.depends('failure_load_kn', 'cross_section_area')
    def _compute_strength(self):
        for rec in self:
            if rec.failure_load_kn and rec.cross_section_area:
                rec.compressive_strength = (rec.failure_load_kn * 1000) / rec.cross_section_area
            else:
                rec.compressive_strength = 0.0

    @api.depends('compressive_strength', 'target_strength')
    def _compute_result(self):
        for rec in self:
            if not rec.compressive_strength:
                rec.result = 'pending'
            elif rec.target_strength and rec.compressive_strength >= rec.target_strength:
                rec.result = 'pass'
            else:
                rec.result = 'fail'

    def action_record_test(self):
        self.write({'state': 'tested', 'test_date': fields.Date.today()})
        # Auto-create NCR on failure
        for rec in self.filtered(lambda r: r.result == 'fail' and not r.ncr_id):
            ncr = self.env['ready.mix.ncr'].create({
                'load_id': rec.load_id.id,
                'source': 'sample',
                'description': _('Specimen %s failed at %d days: %.1f MPa vs target %.1f MPa') % (
                    rec.name, rec.test_age_days,
                    rec.compressive_strength, rec.target_strength),
            })
            rec.ncr_id = ncr.id

    def action_certify(self):
        self.write({'state': 'certified', 'certificate_issued': True})

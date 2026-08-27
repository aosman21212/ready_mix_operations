from odoo import models, fields, api, _


class ReadyMixQCTest(models.Model):
    _name = 'ready.mix.qc.test'
    _description = 'Fresh QC Test'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'test_date desc, name'

    name = fields.Char(string='Test Reference', required=True, copy=False,
                        default=lambda self: _('New'), tracking=True)
    load_id = fields.Many2one('ready.mix.load', string='Load Ticket', required=True,
                               ondelete='cascade', tracking=True)
    plant_id = fields.Many2one(related='load_id.plant_id', string='Plant', store=True)
    partner_id = fields.Many2one(related='load_id.partner_id', string='Customer', store=True)
    mix_product_id = fields.Many2one(related='load_id.mix_product_id', store=True)
    test_date = fields.Date(string='Test Date', required=True, default=fields.Date.today)
    technician_id = fields.Many2one('res.users', string='QC Technician')

    # Fresh test results
    slump = fields.Float(string='Slump (mm)', digits=(16, 1))
    air_content = fields.Float(string='Air Content (%)', digits=(16, 2))
    temperature = fields.Float(string='Temperature (°C)', digits=(16, 1))
    density = fields.Float(string='Fresh Density (kg/m³)', digits=(16, 2))
    water_added = fields.Float(string='Water Added at Site (L)', digits=(16, 2))
    wc_ratio = fields.Float(string='W/C Ratio', digits=(16, 3))

    # Pass / Fail per parameter
    slump_pass = fields.Selection([('pass', 'Pass'), ('fail', 'Fail'), ('na', 'N/A')],
                                   string='Slump Result', compute='_compute_results', store=True)
    air_pass = fields.Selection([('pass', 'Pass'), ('fail', 'Fail'), ('na', 'N/A')],
                                 string='Air Result', compute='_compute_results', store=True)
    overall_result = fields.Selection([('pass', 'Pass'), ('fail', 'Fail'), ('pending', 'Pending')],
                                       string='Overall', compute='_compute_results', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], string='Status', default='draft', tracking=True)
    ncr_id = fields.Many2one('ready.mix.ncr', string='Linked NCR')
    notes = fields.Text(string='Remarks')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ready.mix.qc.test') or _('New')
        return super().create(vals_list)

    @api.depends('slump', 'air_content', 'mix_product_id')
    def _compute_results(self):
        for rec in self:
            mix = rec.mix_product_id
            slump_pass = 'na'
            air_pass = 'na'
            if mix and rec.slump:
                if mix.slump_min <= rec.slump <= mix.slump_max:
                    slump_pass = 'pass'
                else:
                    slump_pass = 'fail'
            if mix and rec.air_content:
                if mix.air_content_min <= rec.air_content <= mix.air_content_max:
                    air_pass = 'pass'
                else:
                    air_pass = 'fail'
            rec.slump_pass = slump_pass
            rec.air_pass = air_pass
            if slump_pass == 'fail' or air_pass == 'fail':
                rec.overall_result = 'fail'
            elif slump_pass == 'pass' or air_pass == 'pass':
                rec.overall_result = 'pass'
            else:
                rec.overall_result = 'pending'

    def action_confirm(self):
        self.write({'state': 'confirmed'})
        # Auto-create NCR if failed
        for rec in self.filtered(lambda r: r.overall_result == 'fail' and not r.ncr_id):
            ncr = self.env['ready.mix.ncr'].create({
                'load_id': rec.load_id.id,
                'source': 'qc_test',
                'description': _('QC Fresh Test failure on Load %s') % rec.load_id.name,
            })
            rec.ncr_id = ncr.id

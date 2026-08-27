from odoo import models, fields, api, _


class ReadyMixNCR(models.Model):
    _name = 'ready.mix.ncr'
    _description = 'Non-Conformance Report (NCR / CAPA)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, name'

    name = fields.Char(string='NCR Reference', required=True, copy=False,
                        default=lambda self: _('New'), tracking=True)
    load_id = fields.Many2one('ready.mix.load', string='Load Ticket', ondelete='set null')
    plant_id = fields.Many2one(related='load_id.plant_id', store=True, string='Plant')
    partner_id = fields.Many2one(related='load_id.partner_id', store=True, string='Customer')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    date = fields.Date(string='Date Raised', required=True, default=fields.Date.today,
                        tracking=True)
    source = fields.Selection([
        ('qc_test', 'QC Fresh Test'),
        ('sample', 'Specimen Test'),
        ('delivery', 'Delivery Issue'),
        ('customer', 'Customer Complaint'),
        ('internal', 'Internal Audit'),
        ('other', 'Other'),
    ], string='Source', required=True, default='other', tracking=True)
    severity = fields.Selection([
        ('minor', 'Minor'),
        ('major', 'Major'),
        ('critical', 'Critical'),
    ], string='Severity', default='minor', tracking=True)
    description = fields.Text(string='Non-Conformance Description', required=True)
    root_cause = fields.Text(string='Root Cause Analysis (8D)')
    immediate_action = fields.Text(string='Immediate / Containment Action')
    corrective_action = fields.Text(string='Corrective Action (CAPA)')
    preventive_action = fields.Text(string='Preventive Action')
    responsible_id = fields.Many2one('res.users', string='Responsible', tracking=True)
    target_close_date = fields.Date(string='Target Close Date', tracking=True)
    actual_close_date = fields.Date(string='Actual Close Date')
    verified_by = fields.Many2one('res.users', string='Verified By')
    verification_date = fields.Date(string='Verification Date')

    state = fields.Selection([
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('pending_verification', 'Pending Verification'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='open', tracking=True)
    notes = fields.Text(string='Additional Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ready.mix.ncr') or _('New')
        return super().create(vals_list)

    def action_in_progress(self):
        self.write({'state': 'in_progress'})

    def action_pending_verification(self):
        self.write({'state': 'pending_verification'})

    def action_close(self):
        self.write({
            'state': 'closed',
            'actual_close_date': fields.Date.today(),
            'verified_by': self.env.user.id,
            'verification_date': fields.Date.today(),
        })

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reopen(self):
        self.write({'state': 'open'})

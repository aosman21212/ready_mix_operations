from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    plant_id = fields.Many2one('ready.mix.plant', string='Concrete Plant')
    jobsite_id = fields.Many2one('ready.mix.jobsite', string='Job Site',
                                  domain="[('partner_id','=',partner_id)]")
    technical_reviewed = fields.Boolean(string='Technical Review Done', tracking=True,
                                         default=False)
    technical_review_date = fields.Date(string='Technical Review Date')
    technical_reviewer_id = fields.Many2one('res.users', string='Reviewed By')
    rate_agreement_id = fields.Many2one('ready.mix.rate.agreement', string='Rate Agreement',
                                         domain="[('partner_id','=',partner_id),('state','=','active')]")

    schedule_ids = fields.One2many('ready.mix.schedule', 'sale_order_id', string='Schedules')
    schedule_count = fields.Integer(compute='_compute_rm_counts')
    load_ids = fields.One2many('ready.mix.load', 'sale_order_id', string='Load Tickets')
    load_count = fields.Integer(compute='_compute_rm_counts')
    delivered_volume = fields.Float(string='Delivered Volume (m³)',
                                     compute='_compute_rm_counts', digits=(16, 2))

    def _compute_rm_counts(self):
        for rec in self:
            rec.schedule_count = len(rec.schedule_ids)
            rec.load_count = len(rec.load_ids)
            rec.delivered_volume = sum(rec.load_ids.filtered(
                lambda l: l.state == 'delivered').mapped('volume_delivered'))

    def action_technical_review(self):
        self.write({
            'technical_reviewed': True,
            'technical_review_date': fields.Date.today(),
            'technical_reviewer_id': self.env.user.id,
        })

    def action_view_schedules(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Delivery Schedules'),
            'res_model': 'ready.mix.schedule',
            'view_mode': 'list,form',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {'default_sale_order_id': self.id,
                        'default_partner_id': self.partner_id.id,
                        'default_plant_id': self.plant_id.id},
        }

    def action_view_loads(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Load Tickets'),
            'res_model': 'ready.mix.load',
            'view_mode': 'list,form',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {'default_sale_order_id': self.id},
        }

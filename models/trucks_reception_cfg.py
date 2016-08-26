from openerp import api, fields, models


class TrucksReceptionCfg(models.TransientModel):
    _inherit = 'res.config.settings'
    _name = 'trucks.reception.cfg'

    default_max_input_per_contract = fields.Float(default_model='trucks.reception')

    damaged_location = fields.Many2one('stock.location')

    @api.one
    def set_damaged_location(self):
        conf = self.env['ir.config_parameter']
        conf.set_param('trucks.reception.damaged_location', self.damaged_location)

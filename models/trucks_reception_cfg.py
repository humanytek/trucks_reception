from openerp import fields, models


class TrucksReceptionCfg(models.TransientModel):
    _inherit = 'res.config.settings'
    _name = 'trucks.reception.cfg'

    default_max_input_per_contract = fields.Float(default_model='trucks.reception')

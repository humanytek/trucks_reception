from openerp import _, api, exceptions, fields, models


class TrucksReception(models.Model):
    _name = 'trucks.reception'

    contract = fields.Many2one('purchase.order')  # TODO Check ID
    number = fields.Many2one('res.partner')  # TODO
    street = fields.Char(readonly=True, related='number.street')

    driver = fields.Many2one('res.partner')
    car_plates = fields.Char()

    contract_type = fields.Selection(readonly=True, related="contract.contract_type")
    hired = fields.Float(readonly=True)  # TODO Related with contract
    delivered = fields.Float(readonly=True)  # TODO
    pending = fields.Float(readonly=True)  # TODO

    product = fields.Many2one('product.product')
    dest = fields.Many2one('stock.location')
    location = fields.Many2one('stock.location')

    humidity = fields.Float(min_value=0)
    density = fields.Float(min_value=0)
    temperature = fields.Float(min_value=0)

    damaged = fields.Float(min_value=0, max_value=10)
    broken = fields.Float(min_value=0)
    impurities = fields.Float(min_value=0)

    transgenic = fields.Float(min_value=0)

    ticket = fields.Integer()
    other_specs = fields.Selection([
        # TODO
    ])

    weight_input = fields.Float(min_value=0)
    weight_output = fields.Float(min_value=0)
    weight_neto = fields.Float(compute="_compute_weight_neto", store=False)

    kilos_damaged = fields.Float(compute="_compute_kilos_damaged", store=False)
    kilos_broken = fields.Float(compute="_compute_kilos_broken", store=False)
    kilos_impurities = fields.Float(compute="_compute_kilos_impurities", store=False)
    kilos_humidity = fields.Float(compute="_compute_kilos_humidity", store=False)
    weight_neto_analized = fields.Float(compute="_compute_weight_neto_analized", store=False)

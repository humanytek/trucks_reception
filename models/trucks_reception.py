from openerp import _, api, exceptions, fields, models


class TrucksReception(models.Model):
    _name = 'trucks.reception'

    name = fields.Char()

    state = fields.Selection([
        ('analysis', 'Analysis'),
        ('weight_input', 'Weight Input'),
        ('unloading', 'Unloading'),
        ('weight_output', 'Weight Output'),
        ('done', 'Done'),
    ])

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

    _defaults = {'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'reg_code'), }

    @api.depends('weight_input', 'weight_output')
    def _compute_weight_neto(self):
        self.weight_neto = self.weight_input - self.weight_output

    @api.depends('weight_neto', 'damaged')
    def _compute_kilos_damaged(self):
        if self.damaged > 5:
            self.kilos_damaged = ((self.damaged - 5) / 10) * self.weight_neto
        else:
            self.kilos_damaged = 0

    @api.depends('weight_neto', 'broken')
    def _compute_kilos_broken(self):
        if self.broken > 2:
            self.kilos_broken = ((self.broken - 2) / 10) * self.weight_neto
        else:
            self.kilos_broken = 0

    @api.depends('weight_neto', 'impurities')
    def _compute_kilos_impurities(self):
        if self.impurities > 2:
            self.kilos_impurities = ((self.impurities - 2) / 10) * self.weight_neto
        else:
            self.kilos_impurities = 0

    @api.depends('weight_neto', 'humidity')
    def _compute_kilos_humidity(self):
        if self.humidity > 14:
            self.kilos_humidity = ((self.humidity - 14) * .116) * self.weight_neto
        else:
            self.kilos_humidity = 0

    @api.constrains('humidity')
    def _constrains_humidity(self):
        if self.humidity >= 17:
            raise exceptions.ValidationError(_('Can not accept that product, humidity over 17'))

    @api.onchange('humidity')
    def _onchange_humidity(self):
        if self.humidity >= 16 and self.humidity < 17:
            return {
                'warning': {
                    'title': _('Humidity high'),
                    'message': _('Can not storage that product, humidity over 16')
                }
            }

    @api.depends('weight_neto', 'kilos_damaged', 'kilos_broken', 'kilos_impurities', 'kilos_humidity')
    def _compute_weight_neto_analized(self):
        self.weight_neto_analized = self.weight_neto - self.kilos_damaged - self.kilos_broken - self.kilos_impurities - self.kilos_humidity

    @api.multi
    def action_analysis(self):
        self.state = 'analysis'

    @api.multi
    def action_weight_input(self):
        self.state = 'weight_input'

    @api.multi
    def action_unloading(self):
        self.state = 'unloading'

    @api.multi
    def action_weight_output(self):
        self.state = 'weight_output'

    @api.multi
    def action_done(self):
        self.state = 'done'

from openerp import _, api, exceptions, fields, models


class TrucksReception(models.Model):
    _name = 'trucks.reception'
    _inherit = ['mail.thread']

    name = fields.Char()

    state = fields.Selection([
        ('analysis', 'Analysis'),
        ('weight_input', 'Weight Input'),
        ('unloading', 'Unloading'),
        ('weight_output', 'Weight Output'),
        ('done', 'Done'),
    ], default='analysis')

    contract_id = fields.Many2one('purchase.order')
    contract_type = fields.Selection(readonly=True, related="contract_id.contract_type")
    partner_id = fields.Many2one('res.partner', related="contract_id.partner_id", readonly=True)
    street = fields.Char(readonly=True, related='partner_id.street')

    driver = fields.Char()
    car_plates = fields.Char()

    hired = fields.Float(readonly=True, compute="_compute_hired", store=False)
    delivered = fields.Float(readonly=True, compute="_compute_delivered", store=False)
    pending = fields.Float(readonly=True, compute="_compute_pending", store=False)

    product_id = fields.Many2one('product.product', compute="_compute_product_id", store=False, readonly=True)
    location_id = fields.Many2one('stock.location', related="contract_id.location_id", readonly=True)

    humidity = fields.Float(min_value=0)
    density = fields.Float(min_value=0)
    temperature = fields.Float(min_value=0)

    damaged = fields.Float(min_value=0, max_value=10)
    broken = fields.Float(min_value=0)
    impurities = fields.Float(min_value=0)

    transgenic = fields.Float(min_value=0)

    ticket = fields.Char()

    weight_input = fields.Float(min_value=0)
    weight_output = fields.Float(min_value=0)
    weight_neto = fields.Float(compute="_compute_weight_neto", store=False)

    kilos_damaged = fields.Float(compute="_compute_kilos_damaged", store=False)
    kilos_broken = fields.Float(compute="_compute_kilos_broken", store=False)
    kilos_impurities = fields.Float(compute="_compute_kilos_impurities", store=False)
    kilos_humidity = fields.Float(compute="_compute_kilos_humidity", store=False)
    weight_neto_analized = fields.Float(compute="_compute_weight_neto_analized", store=False)

    stock_picking_id = fields.Many2one('stock.picking', readonly=True)

    _defaults = {'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'reg_code'), }

    @api.one
    @api.depends('weight_input', 'weight_output')
    def _compute_weight_neto(self):
        self.weight_neto = self.weight_input - self.weight_output

    @api.one
    @api.depends('weight_neto', 'damaged')
    def _compute_kilos_damaged(self):
        if self.damaged > 5:
            self.kilos_damaged = ((self.damaged - 5) / 1000) * self.weight_neto
        else:
            self.kilos_damaged = 0

    @api.one
    @api.depends('weight_neto', 'broken')
    def _compute_kilos_broken(self):
        if self.broken > 2:
            self.kilos_broken = ((self.broken - 2) / 1000) * self.weight_neto
        else:
            self.kilos_broken = 0

    @api.one
    @api.depends('weight_neto', 'impurities')
    def _compute_kilos_impurities(self):
        if self.impurities > 2:
            self.kilos_impurities = ((self.impurities - 2) / 1000) * self.weight_neto
        else:
            self.kilos_impurities = 0

    @api.one
    @api.depends('weight_neto', 'humidity')
    def _compute_kilos_humidity(self):
        if self.humidity > 14:
            self.kilos_humidity = ((self.humidity - 14) * .0116) * self.weight_neto
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

    @api.one
    @api.depends('weight_neto', 'kilos_damaged', 'kilos_broken', 'kilos_impurities', 'kilos_humidity')
    def _compute_weight_neto_analized(self):
        self.weight_neto_analized = self.weight_neto - self.kilos_damaged - self.kilos_broken - self.kilos_impurities - self.kilos_humidity

    @api.one
    @api.depends('contract_id')
    def _compute_hired(self):
        self.hired = sum(line.product_qty for line in self.contract_id.order_line)

    @api.one
    @api.depends('contract_id', 'weight_neto')
    def _compute_delivered(self):
        self.delivered = sum(record.weight_neto for record in self.contract_id.trucks_reception_ids) / 1000

    @api.one
    @api.depends('contract_id')
    def _compute_pending(self):
        self.pending = self.hired - self.delivered

    @api.one
    @api.depends('contract_id')
    def _compute_product_id(self):
        product_id = False
        for line in self.contract_id.order_line:
            product_id = line.product_id
            break
        self.product_id = product_id

    @api.one
    def fun_unload(self):
        self.state = 'weight_output'

    @api.multi
    def fun_finalize(self):
        self.state = 'done'
        self.stock_picking_id = self.env['stock.picking'].search([('origin', '=', self.contract_id.name), ('state', '=', 'assigned')], order='date', limit=1)
        if self.stock_picking_id:
            picking = [self.stock_picking_id.id]
            return self._do_enter_transfer_details(picking, self.stock_picking_id, self.weight_neto, self.location_id)

    @api.multi
    def _do_enter_transfer_details(self, picking_id, picking, weight_neto, location_id, context=None):
        if not context:
            context = {}
        else:
            context = context.copy()
        context.update({
            'active_model': self._name,
            'active_ids': picking_id,
            'active_id': len(picking_id) and picking_id[0] or False
        })

        created_id = self.env['stock.transfer_details'].create({'picking_id': len(picking_id) and picking_id[0] or False})

        items = []
        # for op in picking.pack_operation_ids:
        #     item = {
        #         'packop_id': op.id,
        #         'product_id': op.product_id.id,
        #         'product_uom_id': op.product_uom_id.id,
        #         'quantity': op.product_qty,
        #         'package_id': op.package_id.id,
        #         'lot_id': op.lot_id.id,
        #         'sourceloc_id': op.location_id.id,
        #         'destinationloc_id': op.location_dest_id.id,
        #         'result_package_id': op.result_package_id.id,
        #         'date': op.date,
        #         'owner_id': op.owner_id.id,
        #     }
        #     if op.product_id:
        #         items.append(item)
        #     elif op.package_id:
        #         packs.append(item)
        created_id.item_ids = items
        # created_id.do_detailed_transfer()
        return created_id.wizard_view()

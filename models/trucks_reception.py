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
    auxiliary_contract = fields.Many2one('purchase.order')
    contract_type = fields.Selection(readonly=True, related="contract_id.contract_type")
    partner_id = fields.Many2one('res.partner', related="contract_id.partner_id", readonly=True)
    street = fields.Char(readonly=True, related='partner_id.street')
    shipped = fields.Boolean(related='contract_id.shipped')
    contract_state = fields.Selection(related="contract_id.state")

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

    damaged_location = fields.Many2one('stock.location')

    _defaults = {'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'reg_code'), }

    @api.one
    @api.depends('weight_input', 'weight_output')
    def _compute_weight_neto(self):
        self.weight_neto = self.weight_input - self.weight_output

    @api.one
    @api.depends('weight_neto', 'damaged')
    def _compute_kilos_damaged(self):
        if self.damaged > 5:
            self.kilos_damaged = ((self.damaged - 5) / 100) * self.weight_neto
        else:
            self.kilos_damaged = 0

    @api.one
    @api.depends('weight_neto', 'broken')
    def _compute_kilos_broken(self):
        if self.broken > 2:
            self.kilos_broken = ((self.broken - 2) / 100) * self.weight_neto
        else:
            self.kilos_broken = 0

    @api.one
    @api.depends('weight_neto', 'impurities')
    def _compute_kilos_impurities(self):
        if self.impurities > 2:
            self.kilos_impurities = ((self.impurities - 2) / 100) * self.weight_neto
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
    @api.depends('contract_id', 'weight_neto_analized')
    def _compute_delivered(self):
        self.delivered = sum(record.weight_neto_analized for record in self.contract_id.trucks_reception_ids) / 1000

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
    def fun_transfer(self):
        self.state = 'done'
        self.stock_picking_id = self.env['stock.picking'].search([('origin', '=', self.contract_id.name), ('state', '=', 'assigned')], order='date', limit=1)
        if self.stock_picking_id:
            picking = [self.stock_picking_id.id]
            if self.weight_neto_analized <= self.hired:
                self._do_enter_transfer_details(picking, self.stock_picking_id, self.weight_neto_analized, self.location_id)
            else:
                self._do_enter_transfer_details(picking, self.stock_picking_id, self.hired, self.location_id)
                self.auxiliary_contract = self.env['purchase.order'].create({'partner_id': self.contract_id.partner_id.id,
                                                                             'location_id': self.contract_id.location_id.id,
                                                                             'pricelist_id': self.contract_id.pricelist_id.id})
                self.auxiliary_contract.order_line = self.env['purchase.order.line'].create({
                    'order_id': self.auxiliary_contract.id,
                    'product_id': self.contract_id.order_line[0].product_id.id,
                    'name': self.contract_id.order_line[0].name,
                    'date_planned': self.contract_id.order_line[0].date_planned,
                    'company_id': self.contract_id.order_line[0].company_id.id,
                    'product_qty': (self.weight_neto_analized/1000 - self.hired),
                    'price_unit': self.contract_id.order_line[0].price_unit,
                })
                self.fun_ship()

    @api.multi
    def fun_ship(self):
        stock_picking_id_cancel = self.env['stock.picking'].search([('origin', '=', self.contract_id.name), ('state', '=', 'assigned')], order='date', limit=1)
        if stock_picking_id_cancel:
            stock_picking_id_cancel.action_cancel()

    @api.multi
    def _do_enter_transfer_details(self, picking_id, picking, weight_neto_analized, location_id, context=None):
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
        if not picking.pack_operation_ids:
            picking.do_prepare_partial()
        for op in picking.pack_operation_ids:
            item = {
                'packop_id': op.id,
                'product_id': op.product_id.id,
                'product_uom_id': op.product_uom_id.id,
                'quantity': weight_neto_analized/1000,
                'package_id': op.package_id.id,
                'lot_id': op.lot_id.id,
                'sourceloc_id': op.location_id.id,
                'destinationloc_id': op.location_dest_id.id,
                'result_package_id': op.result_package_id.id,
                'date': op.date,
                'owner_id': op.owner_id.id,
            }
            if op.product_id:
                items.append(item)
        created_id.item_ids = items
        created_id.do_detailed_transfer()

    @api.multi
    def write(self, vals, recursive=None):
        if not recursive:
            if self.state == 'analysis':
                self.write({'state': 'weight_input'}, 'r')
            elif self.state == 'weight_input':
                self.write({'state': 'unloading'}, 'r')
            elif self.state == 'unloading':
                self.write({'state': 'weight_output'}, 'r')
            elif self.state == 'weight_output':
                self.write({'state': 'done'}, 'r')

        res = super(TrucksReception, self).write(vals)
        return res

    @api.model
    def create(self, vals):
        vals['state'] = 'weight_input'
        res = super(TrucksReception, self).create(vals)
        return res

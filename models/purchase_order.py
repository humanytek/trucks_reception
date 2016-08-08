from openerp import fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    trucks_reception_ids = fields.One2many('trucks.reception', 'contract_id')

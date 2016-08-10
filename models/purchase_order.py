from openerp import fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    trucks_reception_ids = fields.One2many('trucks.reception', 'contract_id')

    def trucks_reception(self, cr, uid, ids, context=None):
        '''
        This function returns an action that display existing picking orders of given purchase order ids.
        '''
        if context is None:
            context = {}
        mod_obj = self.pool.get('ir.model.data')
        dummy, action_id = tuple(mod_obj.get_object_reference(cr, uid, 'trucks_reception', 'trucks_reception_list_action'))
        action = self.pool.get('ir.actions.act_window').read(cr, uid, action_id, context=context)

        pick_ids = []
        for po in self.browse(cr, uid, ids, context=context):
            pick_ids += [picking.id for picking in po.trucks_reception_ids]

        # override the context to get rid of the default filtering on picking type
        action['context'] = {}
        # choose the view_mode accordingly
        if len(pick_ids) > 1:
            action['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        else:
            # TODO
            action['context'] = {'default_contract_id': '1'}
            res = mod_obj.get_object_reference(cr, uid, 'trucks_reception', 'trucks_reception_form_view')
            action['views'] = [(res and res[1] or False, 'form')]
            # action['res_id'] = pick_ids and pick_ids[0] or False
        return action

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_confirm(self, merge=True, merge_into=False):
        """Hook del flujo de procurement (reabastecimiento automático): tras confirmar
        los moves, setea la sucursal destino en los pickings hacia tránsito.

        En O19 los pickings generados por procurement NO pasan por
        stock.picking.action_confirm; el override de action_confirm solo cubre la
        confirmación manual. Este es el hook que sí se dispara en el flujo automático.
        """
        moves = super()._action_confirm(merge=merge, merge_into=merge_into)
        pickings = moves.picking_id.filtered(
            lambda p: p.location_dest_id and p.location_dest_id.usage == 'transit')
        if pickings:
            pickings._yaguven_set_branch_partner()
        return moves

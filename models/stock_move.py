from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_confirm(self, merge=True, merge_into=False, **kwargs):
        """Hook del flujo de procurement (reabastecimiento automático): tras confirmar
        los moves, setea la sucursal destino en los pickings hacia tránsito.

        En O19 los pickings generados por procurement NO pasan por
        stock.picking.action_confirm; el override de action_confirm solo cubre la
        confirmación manual. Este es el hook que sí se dispara en el flujo automático.

        IMPORTANTE: aceptar y reenviar **kwargs. El core de O19 llama a
        _action_confirm(merge=..., create_proc=...) desde _create_backorder; una firma
        fija que no acepte create_proc rompe la validación de TODA recepción/entrega
        (TypeError aunque el recordset de backorder esté vacío, porque la firma se
        valida al invocar). v1.0.6.
        """
        moves = super()._action_confirm(merge=merge, merge_into=merge_into, **kwargs)
        # tránsito (2 pasos) o interno (reparto 1 paso entre almacenes); el gating fino
        # lo hace _yaguven_resolve_partner (no toca recepciones/entregas ni intra-almacén). v1.0.7
        pickings = moves.picking_id.filtered(
            lambda p: p.location_dest_id and p.location_dest_id.usage in ('transit', 'internal'))
        if pickings:
            pickings._yaguven_set_branch_partner()
        return moves

from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    yaguven_partner_destino_id = fields.Many2one(
        comodel_name='res.partner',
        string='Sucursal destino',
        compute='_compute_yaguven_partner_destino',
    )

    @api.depends('move_ids.move_dest_ids', 'move_ids.rule_id',
                 'picking_type_code', 'location_dest_id')
    def _compute_yaguven_partner_destino(self):
        for picking in self:
            picking.yaguven_partner_destino_id = picking._yaguven_resolve_partner()

    def _yaguven_resolve_partner(self):
        """Return the destination branch partner for an OUT-to-transit internal picking."""
        self.ensure_one()
        if self.picking_type_code != 'internal' or self.location_dest_id.usage != 'transit':
            return self.env['res.partner']
        WhSudo = self.env['stock.warehouse'].sudo()
        for move in self.move_ids:
            for dest_move in move.move_dest_ids:
                loc = dest_move.location_dest_id
                wh = WhSudo.search([('lot_stock_id', '=', loc.id)], limit=1)
                if not wh:
                    pids = [int(x) for x in (loc.parent_path or '').strip('/').split('/') if x]
                    wh = WhSudo.search([('view_location_id', 'in', pids)], limit=1)
                if wh and wh.partner_id:
                    return wh.partner_id
        # fallback: partner_address_id cargado en la regla por pieza2d
        for move in self.move_ids:
            if move.rule_id and move.rule_id.partner_address_id:
                return move.rule_id.partner_address_id
        return self.env['res.partner']

    def action_confirm(self):
        res = super().action_confirm()
        for picking in self:
            if picking.picking_type_code != 'internal':
                continue
            if picking.location_dest_id.usage != 'transit':
                continue
            partner = picking._yaguven_resolve_partner()
            if partner and picking.partner_id != partner:
                picking.write({'partner_id': partner.id})
        return res

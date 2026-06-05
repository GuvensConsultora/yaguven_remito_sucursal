from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    yaguven_partner_destino_id = fields.Many2one(
        comodel_name='res.partner',
        string='Sucursal destino',
        compute='_compute_yaguven_partner_destino',
    )

    @api.depends('move_ids', 'picking_type_code', 'location_dest_id')
    def _compute_yaguven_partner_destino(self):
        for picking in self:
            picking.yaguven_partner_destino_id = picking._yaguven_resolve_partner()

    def _yaguven_resolve_partner(self):
        """Return the destination branch partner for an OUT-to-transit internal picking."""
        self.ensure_one()
        if self.picking_type_code != 'internal':
            return self.env['res.partner']
        loc_dest = self.location_dest_id
        if not loc_dest or loc_dest.usage != 'transit':
            return self.env['res.partner']
        WhSudo = self.env['stock.warehouse'].sudo()
        MoveSudo = self.env['stock.move'].sudo()
        # search_read fuerza lectura directa a DB (probado que funciona en O19)
        move_rows = MoveSudo.search_read(
            [('picking_id', '=', self.id), ('state', '!=', 'cancel')],
            ['id', 'move_dest_ids', 'rule_id'],
        )
        for mv in move_rows:
            dest_ids = mv.get('move_dest_ids') or []
            if dest_ids:
                dest_rows = MoveSudo.search_read(
                    [('id', 'in', dest_ids)],
                    ['id', 'location_dest_id'],
                )
                for dm in dest_rows:
                    if not dm.get('location_dest_id'):
                        continue
                    loc_id = dm['location_dest_id'][0]
                    wh = WhSudo.search([('lot_stock_id', '=', loc_id)], limit=1)
                    if not wh:
                        loc = self.env['stock.location'].sudo().browse(loc_id)
                        pids = [int(x) for x in (loc.parent_path or '').strip('/').split('/') if x]
                        wh = WhSudo.search([('view_location_id', 'in', pids)], limit=1)
                    if wh and wh.partner_id:
                        return wh.partner_id
        # fallback: partner_address_id de la regla
        for mv in move_rows:
            if mv.get('rule_id'):
                rule = self.env['stock.rule'].sudo().browse(mv['rule_id'][0])
                if rule.partner_address_id:
                    return rule.partner_address_id
        return self.env['res.partner']

    def action_confirm(self):
        res = super().action_confirm()
        for picking in self:
            if picking.picking_type_code != 'internal':
                continue
            if not picking.location_dest_id or picking.location_dest_id.usage != 'transit':
                continue
            partner = picking._yaguven_resolve_partner()
            if partner and picking.partner_id != partner:
                picking.write({'partner_id': partner.id})
        return res

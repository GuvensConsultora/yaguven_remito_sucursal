from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    yaguven_partner_destino_id = fields.Many2one(
        comodel_name='res.partner',
        string='Sucursal destino',
        compute='_compute_yaguven_partner_destino',
    )

    @api.depends('location_dest_id')
    def _compute_yaguven_partner_destino(self):
        for picking in self:
            picking.yaguven_partner_destino_id = picking._yaguven_resolve_partner()

    def _yaguven_resolve_partner(self):
        """Sucursal destino de un picking cuyo destino es una ubicación de tránsito.

        Resuelve por la UBICACIÓN DE TRÁNSITO (no por la cadena de moves, que en
        O19 puede venir vacía): tránsito -> regla IN (src=tránsito) -> depósito de
        la sucursal -> almacén -> partner. Robusto e independiente del estado.
        """
        self.ensure_one()
        loc_dest = self.location_dest_id
        if not loc_dest or loc_dest.usage != 'transit':
            return self.env['res.partner']
        Rule = self.env['stock.rule'].sudo()
        Wh = self.env['stock.warehouse'].sudo()
        Loc = self.env['stock.location'].sudo()
        # regla IN: location_src_id = este tránsito -> location_dest_id = depósito sucursal
        in_rules = Rule.search_read(
            [('location_src_id', '=', loc_dest.id)], ['location_dest_id'])
        for r in in_rules:
            if not r.get('location_dest_id'):
                continue
            loc_id = r['location_dest_id'][0]
            wh = Wh.search([('lot_stock_id', '=', loc_id)], limit=1)
            if not wh:
                loc = Loc.browse(loc_id)
                pids = [int(x) for x in (loc.parent_path or '').strip('/').split('/') if x]
                if pids:
                    wh = Wh.search([('view_location_id', 'in', pids)], limit=1)
            if wh and wh.partner_id:
                return wh.partner_id
        # fallback: partner_address_id de la regla del propio move (OUT)
        MoveSudo = self.env['stock.move'].sudo()
        for mv in MoveSudo.search_read(
                [('picking_id', '=', self.id), ('state', '!=', 'cancel')], ['rule_id']):
            if mv.get('rule_id'):
                rule = Rule.browse(mv['rule_id'][0])
                if rule.partner_address_id:
                    return rule.partner_address_id
        return self.env['res.partner']

    def _yaguven_set_branch_partner(self):
        """Setea partner_id = sucursal destino en los pickings hacia tránsito (idempotente)."""
        for picking in self:
            dest = picking.location_dest_id
            if not dest or dest.usage != 'transit':
                continue
            partner = picking._yaguven_resolve_partner()
            if partner and picking.partner_id.id != partner.id:
                picking.write({'partner_id': partner.id})

    def action_confirm(self):
        res = super().action_confirm()
        self._yaguven_set_branch_partner()
        return res

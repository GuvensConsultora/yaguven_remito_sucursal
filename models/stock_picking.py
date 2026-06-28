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
        """Sucursal destino del picking de reparto/reabastecimiento entre almacenes.

        Cubre las dos topologías de reabastecimiento:
        - 1 PASO (sin tránsito): destino = Existencias de un almacén sucursal y origen =
          Existencias de OTRO almacén -> partner del almacén destino. Scope estricto
          (ambos extremos = Existencias de almacén, distintos) para NO tocar recepciones
          de proveedor, entregas a cliente ni movimientos intra-almacén.
        - 2 PASOS (con tránsito): destino = ubicación de tránsito -> regla IN (src=tránsito)
          -> depósito de la sucursal -> almacén -> partner. Independiente de la cadena de
          moves (en O19 puede venir vacía).
        """
        self.ensure_one()
        loc_dest = self.location_dest_id
        if not loc_dest:
            return self.env['res.partner']
        Wh = self.env['stock.warehouse'].sudo()
        # --- caso 1 PASO: reparto inter-almacén Existencias -> Existencias ---
        if loc_dest.usage == 'internal':
            wh_dest = Wh.search([('lot_stock_id', '=', loc_dest.id)], limit=1)
            wh_src = Wh.search([('lot_stock_id', '=', self.location_id.id)], limit=1) \
                if self.location_id else Wh.browse()
            if wh_dest and wh_src and wh_src.id != wh_dest.id and wh_dest.partner_id:
                return wh_dest.partner_id
            return self.env['res.partner']
        # --- caso 2 PASOS: destino tránsito ---
        if loc_dest.usage != 'transit':
            return self.env['res.partner']
        Rule = self.env['stock.rule'].sudo()
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
        """Setea partner_id = sucursal destino en los pickings de reparto/reabastecimiento
        (idempotente). El gating lo hace _yaguven_resolve_partner: solo devuelve partner para
        reparto inter-almacén (1 paso) o destino tránsito (2 pasos); vacío en el resto."""
        for picking in self:
            partner = picking._yaguven_resolve_partner()
            if partner and picking.partner_id.id != partner.id:
                picking.write({'partner_id': partner.id})

    def action_confirm(self):
        res = super().action_confirm()
        self._yaguven_set_branch_partner()
        return res

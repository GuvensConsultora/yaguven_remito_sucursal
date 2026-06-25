{
    'name': 'Yagüven - Remito Sucursal Destino',
    'version': '19.0.1.0.5',
    'summary': 'Corrige partner_id en pickings OUT de traslado: muestra sucursal destino en ficha y remito.',
    'description': 'Setea la sucursal destino en pickings hacia tránsito tanto en confirmación manual '
                   '(action_confirm) como en el flujo automático de reabastecimiento (stock.move._action_confirm), '
                   'resolviendo la sucursal por la ubicación de tránsito (regla IN -> almacén -> partner).',
    'author': 'Yagüven C.G.',
    'category': 'Inventory',
    'license': 'LGPL-3',
    'depends': ['stock', 'l10n_ar_stock'],
    'data': [
        'report/remito_destino.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

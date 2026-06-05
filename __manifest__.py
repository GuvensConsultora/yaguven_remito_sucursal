{
    'name': 'Yagüven - Remito Sucursal Destino',
    'version': '19.0.1.0.3',
    'summary': 'Corrige partner_id en pickings OUT de traslado: muestra sucursal destino en ficha y remito.',
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

{
    'name': 'Trucks Reception',
    'version': '1.0',
    'author': 'Humanytek',
    'website': 'http://humanytek.com',
    'depends': ['purchase', 'purchase_contract_type'],
    'data': [
        'security/ir.model.access.csv',
        'security/trucks_reception_access_rules.xml',
        'views/trucks_reception.xml',
        'views/trucks_reception_cfg.xml',
        'views/purchase_order.xml',
    ]
}

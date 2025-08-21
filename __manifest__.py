{
    'name': '🏟️ Volan Sport Management System',
    'version': '2.0.0',
    'summary': 'Badminton və Basketbol üçün tam idman idarəetmə sistemi',

    'author': 'Volan Sport Center',
    'website': 'https://github.com/7aim/BadmintonOdoo',
    'category': 'Services/Sport Management',
    'license': 'LGPL-3',
    'depends': ['base', 'contacts', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/menu_views.xml',
        'views/res_partner_views.xml',
        'views/sport_system_views.xml',
        'views/badminton_session_views.xml',
        'views/qr_scanner_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 1,
    'external_dependencies': {
        'python': ['qrcode', 'pillow'],
    },
}

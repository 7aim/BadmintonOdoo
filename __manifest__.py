{
    'name': '🏟️ Volan Sport Management System',
    'version': '2.1.0',
    'summary': 'Badminton və Basketbol üçün tam idman idarəetmə sistemi',

    'author': 'Volan Sport Center',
    'website': 'https://github.com/7aim/BadmintonOdoo',
    'category': 'Services/Sport Management',
    'license': 'LGPL-3',
    'images': [
        'static/description/icon.png',
    ],
    'depends': ['base', 'contacts', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/res_partner_views.xml',
        'views/sport_system_views.xml',
        'views/badminton_session_views.xml',
        'views/badminton_sale_views.xml',
        'views/badminton_lesson_views.xml',
        'views/customer_wizard_views.xml',
        'views/qr_scanner_views.xml',
        'views/session_extend_wizard_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'volan_badminton/static/src/css/style.css',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 1,
    'external_dependencies': {
        'python': ['qrcode', 'pillow'],
    },
    'web_icon': 'volan_badminton/static/description/icon.png'
}

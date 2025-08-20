{
    'name': 'Volan Badminton Management',
    'version': '1.0',
    'summary': 'Custom module for Volan Badminton operations.',
    'description': 'Adds custom fields for customers, QR codes, and session management.',
    'author': 'Sizin Adınız',
    'category': 'Services/Sport',
    'depends': ['contacts', 'mail'],
    'data': [
        'views/res_partner_views.xml',
        'views/badminton_session_views.xml',
        'views/qr_scanner_views.xml',
        'data/sequence.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

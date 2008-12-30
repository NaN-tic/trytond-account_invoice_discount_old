#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
{
    'name': 'Account Invoice Discount',
    'name_de_DE': 'Rabattspalte für Rechnung',
    'version': '0.0.1',
    'author': 'virtual things',
    'email': 'info@virtual-things.biz',
    'website': 'http://www.virtual-things.biz/',
    'description': '''This module adds a discount column on invoice
''',
    'description_de_DE': '''Dieses Modul fügt dem Rechnungsformular eine
    Rabattspalte hinzu
''',
    'depends': [
        'account_invoice'
        ],
    'xml': [
        'invoice.xml'
        ],
#    'translation': [
#        'de_DE.csv'
#    ],
}

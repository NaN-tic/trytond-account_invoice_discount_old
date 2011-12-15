#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
{
    'name': 'Account Invoice Discount',
    'name_de_DE': 'Fakturierung Rabatt',
    'version': '2.1.1',
    'author': 'virtual things',
    'email': 'info@virtual-things.biz',
    'website': 'http://www.virtual-things.biz/',
    'description': '''
    - Define discounts for invoice lines
    - Adds field discount in report invoice
''',
    'description_de_DE': '''
    - Ermöglicht die Eingabe von Rabatten pro Rechnungszeile
    - Fügt Rabattfeld im Bericht Rechnung hinzu
''',
    'depends': [
        'account_invoice'
        ],
    'xml': [
        'invoice.xml'
        ],
    'translation': [
        'locale/de_DE.po'
    ],
}

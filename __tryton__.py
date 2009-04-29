#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
{
    'name': 'BETA: Account Invoice Discount',
    'name_de_DE': 'BETA: Fakturierung Rabatt',
    'version': '1.1.0',
    'author': 'virtual things',
    'email': 'info@virtual-things.biz',
    'website': 'http://www.virtual-things.biz/',
    'description': '''WARNING: BETA STATUS
This module is in public testing phase and not yet released.
Never use this module in productive environment. You can not
uninstall this module once it is installed. Watch
www.tryton.org/news.html for release announcements.

Use this module only for testing purposes and submit your issues to
http://bugs.tryton.org. Please note your testing results on
http://code.google.com/p/tryton/wiki/Testing1_2_0#External_Modules.

Define discounts for invoice lines
- with additional field discount in report invoice
''',
    #'description_de_DE': '''Ermöglicht die Eingabe von Rabatten pro Rechnungszeile
    #- mit zusätzlichem Rabattfeld im Bericht Rechnung
#''',
    'depends': [
        'account_invoice'
        ],
    'xml': [
        'invoice.xml'
        ],
    'translation': [
        'de_DE.csv'
    ],
}

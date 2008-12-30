#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.osv import fields, OSV
from decimal import Decimal

class InvoiceLine(OSV):
    'Invoice Line'
    _name = 'account.invoice.line'
    _description = __doc__
    
    discount = fields.Numeric('Discount %', digits=(16, 2))
    amount = fields.Function('get_amount', type='numeric', string='Amount', \
        digits="(16, globals().get('_parent_invoice') and " \
                    "globals().get('_parent_invoice').currency_digits or " \
                    "globals()['currency_digits'])", \
        states={
            'invisible': "type not in ('line', 'subtotal')", \
        }, on_change_with=['type', 'quantity', 'unit_price', \
            '_parent_invoice.currency', 'currency', 'discount'])
    
    def default_discount(self, cursor, user, context=None):
        return 0.0
    
    def on_change_with_amount(self, cursor, user, ids, vals, context=None):
        currency_obj = self.pool.get('currency.currency')
        if vals.get('type') == 'line':
            currency = vals.get('_parent_invoice.currency', vals.get('currency'))
            if isinstance(currency, (int, long)):
                currency = currency_obj.browse(cursor, user, currency, \
                        context=context)
            discount = Decimal(str(vals.get('quantity') or Decimal('0.0'))) * \
                         (vals.get('unit_price') or Decimal('0.0')) * \
                         (((vals.get('discount')* Decimal('0.01'))) or \
                          Decimal('0.0'))
            amount = Decimal(str(vals.get('quantity') or '0.0')) * \
                         (vals.get('unit_price') or Decimal('0.0')) - discount
            if currency:
                return currency_obj.round(cursor, user, currency, amount)
            return amount
        return Decimal('0.0')
    
    def get_amount(self, cursor, user, ids, name, arg, context=None):
        currency_obj = self.pool.get('currency.currency')
        res = {}
        for line in self.browse(cursor, user, ids, context=context):
            if line.type == 'line':
                currency = line.invoice and line.invoice.currency \
                        or line.currency
                res[line.id] = currency_obj.round(cursor, user, currency, \
                        Decimal(str(line.quantity)) * line.unit_price - \
                            (Decimal(str(line.quantity)) * line.unit_price *\
                            (line.discount * Decimal('0.01'))))
            elif line.type == 'subtotal':
                res[line.id] = Decimal('0.0')
                for line2 in line.invoice.lines:
                    if line2.type == 'line':
                        res[line.id] += currency_obj.round(cursor, user, \
                            line2.invoice.currency,
                            Decimal(str(line2.quantity)) * line2.unit_price - \
                            (Decimal(str(line2.quantity)) * line2.unit_price * \
                            (line2.discount * Decimal('0.01'))))
                        print res[line.id]
                    elif line2.type == 'subtotal':
                        if line.id == line2.id:
                            break
                        res[line.id] = Decimal('0.0')
            else:
                res[line.id] = Decimal('0.0')
        return res
    
    def _credit(self, cursor, user, line, context=None):
        '''
        Return values to credit line.
        '''
        res = {}
        for field in ('sequence', 'type', 'quantity', 'unit_price', \
                'description', 'discount'):
            res[field] = line[field]

        for field in ('unit', 'product', 'account'):
            res[field] = line[field].id
            
        res['taxes'] = []
        for tax in line.taxes:
            res['taxes'].append(('add', tax.id))
        return res

InvoiceLine()
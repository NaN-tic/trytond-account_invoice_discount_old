#This file is part account_invoice_discount module for Tryton.
#The COPYRIGHT file at the top level of this repository contains 
#the full copyright notices and license terms.
import copy
from decimal import Decimal
from trytond.model import ModelView, ModelSQL, fields
from trytond.pyson import If, Not, Equal, Eval
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta

__all__ = ['InvoiceLine']
__metaclass__ = PoolMeta

class InvoiceLine:
    'Invoice Line'
    __name__ = 'account.invoice.line'

    discount = fields.Numeric('Discount %',
            digits=(16, Eval('currency_digits', 2)), states={
                'invisible': Not(Equal(Eval('type'), 'line')),
            }, on_change=['discount', 'product', 'quantity', 'type', 'unit_price'],
            depends=['type','unit_price', 'quantity', 'amount'])

    @staticmethod
    def default_discount():
        return 0.0

    def on_change_discount(self):
        res = {}
        if self.discount == Decimal(0.0) and self.quantity != None:
            res['amount'] = Decimal(self.quantity)*self.unit_price
        if self.discount and self.unit_price and self.type == 'line':
            res['amount'] = Decimal(self.quantity)*(self.unit_price -
                self.unit_price * self.discount * Decimal('0.01'))
        return res

    def on_change_product(self):
        res = super(InvoiceLine, self).on_change_product()
        res['discount'] = Decimal(0.0)
        return res

    def get_amount(self, name):
        Currency = Pool().get('currency.currency')
        res = super(InvoiceLine, self).get_amount(name)
        if self.type == 'line':
            currency = self.invoice and self.invoice.currency \
                    or self.currency
            res = Currency.round(currency, \
                    Decimal(str(self.quantity)) * self.unit_price - \
                        (Decimal(str(self.quantity)) * self.unit_price *\
                        (self.discount * Decimal('0.01'))))
        return res

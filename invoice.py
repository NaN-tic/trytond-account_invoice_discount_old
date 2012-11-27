#This file is part account_invoice_discount module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from decimal import Decimal
from trytond.model import fields
from trytond.pyson import Not, Equal, Eval
from trytond.pool import Pool, PoolMeta

__all__ = ['InvoiceLine']
__metaclass__ = PoolMeta


class InvoiceLine:
    'Invoice Line'
    __name__ = 'account.invoice.line'
    discount = fields.Numeric('Discount %',
            digits=(16, Eval('currency_digits', 2)), states={
                'invisible': Not(Equal(Eval('type'), 'line')),
            }, on_change=['discount', 'product',
            'quantity', 'type', 'unit_price'],
            depends=['type', 'unit_price', 'quantity', 'amount'])

    @staticmethod
    def default_discount():
        return Decimal(0.0)

    def on_change_discount(self):
        res = {}
        if self.quantity and self.discount and self.unit_price \
            and self.type == 'line':
            res['unit_price'] = Decimal(self.quantity) * (self.unit_price -
                self.unit_price * self.discount * Decimal('0.01'))
        return res

    def on_change_product(self):
        res = super(InvoiceLine, self).on_change_product()
        res['discount'] = Decimal(0.0)
        return res

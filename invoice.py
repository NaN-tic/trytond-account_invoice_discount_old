#This file is part account_invoice_discount module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from decimal import Decimal
from trytond.model import fields
from trytond.pyson import Not, Equal, Eval
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

__all__ = ['Invoice', 'InvoiceLine']
__metaclass__ = PoolMeta


class Invoice:
    'Invoice Line'
    __name__ = 'account.invoice'

    def _compute_taxes(self):
        '''
        Get taxes from amount, not unit_price
        Price + discount is amount field; Unit Price is origin price
        _compute_taxes in account_invoice get taxes from unit_price
        '''
        Tax = Pool().get('account.tax')

        context = self.get_tax_context()

        res = {}
        for line in self.lines:
            # Don't round on each line to handle rounding error
            if line.type != 'line':
                continue
            unit_price = line.unit_price
            if line.discount and line.discount is not None:
                unit_price =  unit_price - (
                    line.unit_price * (line.discount * Decimal('0.01')))
            with Transaction().set_context(**context):
                taxes = Tax.compute(line.taxes, unit_price,
                        line.quantity)
            for tax in taxes:
                key, val = self._compute_tax(tax, self.type)
                val['invoice'] = self.id
                if not key in res:
                    res[key] = val
                else:
                    res[key]['base'] += val['base']
                    res[key]['amount'] += val['amount']
        for key in res:
            for field in ('base', 'amount'):
                res[key][field] = self.currency.round(res[key][field])
        return res


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
        return Decimal('0.0')

    def on_change_discount(self):
        res = {}
        if self.quantity and self.discount and self.unit_price \
            and self.type == 'line':
            res['amount'] = (self.unit_price -
                self.unit_price * self.discount * Decimal('0.01'))
        return res
    
    def on_change_product(self):
        res = super(InvoiceLine, self).on_change_product()
        res['discount'] = Decimal('0.0')
        return res

    def get_amount(self, name):
        Currency = Pool().get('currency.currency')
        res = super(InvoiceLine, self).get_amount(name)
        if self.type == 'line':
            currency = self.invoice and self.invoice.currency \
                    or self.currency
            res = Currency.round(currency,
                Decimal(str(self.quantity)) * self.unit_price -
                (Decimal(str(self.quantity)) * self.unit_price *
                (self.discount * Decimal('0.01'))))
        return res

    def _compute_taxes(self):
        if self.discount:
            self.unit_price = self.unit_price - (
                self.unit_price * (self.discount * Decimal('0.01')))
        res = super(InvoiceLine, self)._compute_taxes()
        return res

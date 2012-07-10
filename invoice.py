#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import copy
from decimal import Decimal
from trytond.model import ModelView, ModelSQL, fields
from trytond.pyson import Not, Equal, Eval
from trytond.transaction import Transaction
from trytond.pool import Pool


class InvoiceLine(ModelSQL, ModelView):
    _name = 'account.invoice.line'

    discount = fields.Numeric('Discount %',
            digits=(16, Eval('currency_digits', 2)), states={
                'invisible': Not(Equal(Eval('type'), 'line')),
            }, depends=['currency_digits', 'type'])
    def __init__(self):
        super(InvoiceLine, self).__init__()
        self.amount = copy.copy(self.amount)
        if self.amount.on_change_with:
            self.amount.on_change_with.extend(['discount'])
        self._reset_columns()

    def default_discount(self):
        return 0.0

    def on_change_with_amount(self, vals):
        if vals.get('type') == 'line' and vals.get('discount') and \
         vals.get('unit_price'):
            vals = vals.copy()
            vals['unit_price'] = (vals.get('unit_price') -
                vals.get('unit_price') * vals.get('discount') * Decimal('0.01'))
        return super(InvoiceLine, self).on_change_with_amount(vals)

    def get_amount(self, ids, name):
        currency_obj = Pool().get('currency.currency')
        res = super(InvoiceLine, self).get_amount(ids, name)
        for line in self.browse(ids):
            if line.type == 'line':
                currency = line.invoice and line.invoice.currency \
                        or line.currency
                res[line.id] = currency_obj.round(currency, \
                        Decimal(str(line.quantity)) * line.unit_price - \
                            (Decimal(str(line.quantity)) * line.unit_price *\
                            (line.discount * Decimal('0.01'))))
        return res

    def _credit(self, line):
        '''
        Return values to credit line.
        '''
        res = super(InvoiceLine, self)._credit(line)
        res['discount'] = line['discount']
        return res

    def _compute_taxes(self, line):
        pool = Pool()
        tax_obj = pool.get('account.tax')
        currency_obj = pool.get('currency.currency')
        invoice_obj = pool.get('account.invoice')

        context = {}
        context.update(invoice_obj.get_tax_context(line.invoice))
        res = []
        if line.type != 'line':
            return res
        price = line.unit_price - line.unit_price * line.discount / Decimal('100')
        tax_ids = [x.id for x in line.taxes]
        with Transaction().set_context(**context):
            for tax in tax_obj.compute(tax_ids, price, line.quantity):
                if line.invoice.type in ('out_invoice', 'in_invoice'):
                    base_code_id = tax['tax'].invoice_base_code.id
                    amount = tax['base'] * tax['tax'].invoice_base_sign
                else:
                    base_code_id = tax['tax'].credit_note_base_code.id
                    amount = tax['base'] * tax['tax'].credit_note_base_sign
                if base_code_id:
                    with Transaction().set_context(
                            date=line.invoice.currency_date):
                        amount = currency_obj.compute(line.invoice.currency.id,
                            amount, line.invoice.company.currency.id)
                    res.append({
                        'code': base_code_id,
                        'amount': amount,
                    })
        return res

InvoiceLine()


class Invoice(ModelSQL, ModelView):
    _name = 'account.invoice'

    def _compute_taxes(self, invoice):
        tax_obj = Pool().get('account.tax')
        currency_obj = Pool().get('currency.currency')

        context = {}
        context.update(self.get_tax_context(invoice))

        res = {}
        for line in invoice.lines:
            # Don't round on each line to handle rounding error
            if line.type != 'line':
                continue
            price = line.unit_price - line.unit_price * line.discount / Decimal('100')
            tax_ids = [x.id for x in line.taxes]
            with Transaction().set_context(**context):
                for tax in tax_obj.compute(tax_ids, price, line.quantity):
                    key, val = self._compute_tax(tax, invoice.type)
                    val['invoice'] = invoice.id
                    if not key in res:
                        res[key] = val
                    else:
                        res[key]['base'] += val['base']
                        res[key]['amount'] += val['amount']
        return res

    def _on_change_lines_taxes(self, vals):
        currency_obj = Pool().get('currency.currency')
        tax_obj = Pool().get('account.tax')
        res = {
            'untaxed_amount': Decimal('0.0'),
            'tax_amount': Decimal('0.0'),
            'total_amount': Decimal('0.0'),
            'taxes': {},
        }
        currency = None
        if vals.get('currency'):
            currency = currency_obj.browse(vals['currency'])
        computed_taxes = {}
        if vals.get('lines'):
            for line in vals['lines']:
                if line.get('type', 'line') != 'line' or \
                   line.get('unit_price') == None:
                    continue
                res['untaxed_amount'] += line.get('amount') or 0

                discount = line.get('discount')
                if isinstance(discount, float):
                    discount = Decimal(str(line.get('discount')))
                price = line.get('unit_price') - line.get('unit_price') \
                    * discount / Decimal('100')
                for tax in tax_obj.compute(line.get('taxes', []), price,
                        line.get('quantity', 0.0)):
                    key, val = self._compute_tax(tax,
                            vals.get('type', 'out_invoice'))
                    if not key in computed_taxes:
                        computed_taxes[key] = val
                    else:
                        computed_taxes[key]['base'] += val['base']
                        computed_taxes[key]['amount'] += val['amount']
        tax_keys = []
        for tax in vals.get('taxes', []):
            if tax.get('manual', False):
                res['tax_amount'] += tax.get('amount', Decimal('0.0'))
                continue
            key = (tax.get('base_code'), tax.get('base_sign'),
                    tax.get('tax_code'), tax.get('tax_sign'),
                    tax.get('account'), tax.get('description'))
            tax_keys.append(key)
            if key not in computed_taxes:
                res['taxes'].setdefault('remove', [])
                res['taxes']['remove'].append(tax.get('id'))
                continue
            if currency:
                if not currency_obj.is_zero(currency,
                        computed_taxes[key]['base'] - \
                                tax.get('base', Decimal('0.0'))):
                    res['tax_amount'] += computed_taxes[key]['amount']
                    res['taxes'].setdefault('update', [])
                    res['taxes']['update'].append({
                        'id': tax.get('id'),
                        'amount': computed_taxes[key]['amount'],
                        'base': computed_taxes[key]['base'],
                        })
                else:
                    res['tax_amount'] += tax.get('amount', Decimal('0.0'))
            else:
                if computed_taxes[key]['base'] - \
                        tax.get('base', Decimal('0.0')) != Decimal('0.0'):
                    res['tax_amount'] += computed_taxes[key]['amount']
                    res['taxes'].setdefault('update', [])
                    res['taxes']['update'].append({
                        'id': tax.get('id'),
                        'amount': computed_taxes[key]['amount'],
                        'base': computed_taxes[key]['base'],
                        })
                else:
                    res['tax_amount'] += tax.get('amount', Decimal('0.0'))
        for key in computed_taxes:
            if key not in tax_keys:
                res['tax_amount'] += computed_taxes[key]['amount']
                res['taxes'].setdefault('add', [])
                res['taxes']['add'].append(computed_taxes[key])
        if currency:
            res['untaxed_amount'] = currency_obj.round(currency,
                    res['untaxed_amount'])
            res['tax_amount'] = currency_obj.round(currency, res['tax_amount'])
        res['total_amount'] = res['untaxed_amount'] + res['tax_amount']
        if currency:
            res['total_amount'] = currency_obj.round(currency,
                    res['total_amount'])
        return res

Invoice()

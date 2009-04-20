#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from decimal import Decimal
import copy

class InvoiceLine(ModelSQL, ModelView):
    'Invoice Line'
    _name = 'account.invoice.line'

    discount = fields.Numeric('Discount %', digits=(16, 2),
                              states={
                                  'invisible': "type != 'line'",
                                      })
    def __init__(self):
        super(InvoiceLine, self).__init__()
        self.amount = copy.copy(self.amount)
        if self.amount.on_change_with:
            self.amount.on_change_with.extend(['discount'])
        self._reset_columns()

    def default_discount(self, cursor, user, context=None):
        return 0.0

    def on_change_with_amount(self, cursor, user, ids, vals, context=None):
        if vals.get('type') == 'line' and vals.get('discount'):
            vals = vals.copy()
            vals['unit_price'] = (vals.get('unit_price') -
                vals.get('unit_price') * vals.get('discount') * Decimal('0.01'))
        return super(InvoiceLine, self).on_change_with_amount(cursor, user,
                                                ids, vals, context=context)

    def get_amount(self, cursor, user, ids, name, arg, context=None):
        currency_obj = self.pool.get('currency.currency')
        res = super(InvoiceLine, self).get_amount(cursor, user, ids, name, arg,
                                                  context=context)
        for line in self.browse(cursor, user, ids, context=context):
            if line.type == 'line':
                currency = line.invoice and line.invoice.currency \
                        or line.currency
                res[line.id] = currency_obj.round(cursor, user, currency, \
                        Decimal(str(line.quantity)) * line.unit_price - \
                            (Decimal(str(line.quantity)) * line.unit_price *\
                            (line.discount * Decimal('0.01'))))
        return res

    def _credit(self, cursor, user, line, context=None):
        '''
        Return values to credit line.
        '''
        res = super(InvoiceLine, self)._credit(cursor, user, line,
                                                  context=context)
        res['discount'] = line['discount']
        return res

    def _compute_taxes(self, cursor, user, line, context=None):
        tax_obj = self.pool.get('account.tax')
        currency_obj = self.pool.get('currency.currency')
        invoice_obj = self.pool.get('account.invoice')
        if context is None:
            context = {}

        ctx = context.copy()
        ctx.update(invoice_obj.get_tax_context(cursor, user, line.invoice,
            context=context))
        res = []
        if line.type != 'line':
            return res
        price = line.unit_price - line.unit_price * line.discount / Decimal('100')
        tax_ids = [x.id for x in line.taxes]
        for tax in tax_obj.compute(cursor, user, tax_ids, price,
                line.quantity, context=ctx):
            if line.invoice.type in ('out_invoice', 'in_invoice'):
                base_code_id = tax['tax'].invoice_base_code.id
                amount = tax['base'] * tax['tax'].invoice_base_sign
            else:
                base_code_id = tax['tax'].credit_note_base_code.id
                amount = tax['base'] * tax['tax'].credit_note_base_sign
            if base_code_id:
                amount = currency_obj.compute(cursor, user,
                        line.invoice.currency, amount,
                        line.invoice.company.currency, context=context)
                res.append({
                    'code': base_code_id,
                    'amount': amount,
                })
        return res

InvoiceLine()


class Invoice(ModelSQL, ModelView):
    'Invoice'
    _name = 'account.invoice'

    def _compute_taxes(self, cursor, user, invoice, context=None):
        tax_obj = self.pool.get('account.tax')
        currency_obj = self.pool.get('currency.currency')
        if context is None:
            context = {}

        ctx = context.copy()
        ctx.update(self.get_tax_context(cursor, user, invoice,
            context=context))

        res = {}
        for line in invoice.lines:
            # Don't round on each line to handle rounding error
            if line.type != 'line':
                continue
            price = line.unit_price - line.unit_price * line.discount / Decimal('100')
            tax_ids = [x.id for x in line.taxes]
            for tax in tax_obj.compute(cursor, user, tax_ids, price,
                    line.quantity, context=ctx):
                key, val = self._compute_tax(cursor, user, tax, invoice.type,
                        context=context)
                val['invoice'] = invoice.id
                if not key in res:
                    res[key] = val
                else:
                    res[key]['base'] += val['base']
                    res[key]['amount'] += val['amount']
        return res

    def _on_change_lines_taxes(self, cursor, user, ids, vals, context=None):
        currency_obj = self.pool.get('currency.currency')
        tax_obj = self.pool.get('account.tax')
        if context is None:
            context = {}
        res = {
            'untaxed_amount': Decimal('0.0'),
            'tax_amount': Decimal('0.0'),
            'total_amount': Decimal('0.0'),
            'taxes': {},
        }
        currency = None
        if vals.get('currency'):
            currency = currency_obj.browse(cursor, user, vals['currency'],
                    context=context)
        computed_taxes = {}
        if vals.get('lines'):
            ctx = context.copy()
            ctx.update(self.get_tax_context(cursor, user, vals,
                context=context))
            for line in vals['lines']:
                if line.get('type', 'line') != 'line':
                    continue
                res['untaxed_amount'] += line.get('amount', Decimal('0.0'))

                price = line.get('unit_price') - line.get('unit_price') * line.get('discount') / Decimal('100')
                for tax in tax_obj.compute(cursor, user, line.get('taxes', []),
                        price,
                        line.get('quantity', 0.0), context=context):
                    key, val = self._compute_tax(cursor, user, tax,
                            vals.get('type', 'out_invoice'), context=context)
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
                if not currency_obj.is_zero(cursor, user, currency,
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
            res['untaxed_amount'] = currency_obj.round(cursor, user, currency,
                    res['untaxed_amount'])
            res['tax_amount'] = currency_obj.round(cursor, user, currency,
                    res['tax_amount'])
        res['total_amount'] = res['untaxed_amount'] + res['tax_amount']
        if currency:
            res['total_amount'] = currency_obj.round(cursor, user, currency,
                    res['total_amount'])
        return res

Invoice()

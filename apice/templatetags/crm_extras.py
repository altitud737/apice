from django import template

register = template.Library()

@register.filter
def sum_deals_value(deals):
    return sum(deal.value for deal in deals)

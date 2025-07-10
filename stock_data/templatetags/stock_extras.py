from django import template
from django.urls import reverse

register = template.Library()

@register.simple_tag
def get_detail_url(obj):
    """
    Get the appropriate detail URL for a Stock or Index object
    """
    if obj._meta.model_name == 'index':
        return reverse('index_detail', args=[obj.id])
    else:
        return reverse('stock_detail', args=[obj.id])

@register.simple_tag
def is_index(obj):
    """
    Check if the object is an Index
    """
    return obj._meta.model_name == 'index'

@register.simple_tag
def get_display_name(obj):
    """
    Get the appropriate display name for a Stock or Index object
    """
    if obj._meta.model_name == 'index':
        return getattr(obj, 'name', obj.symbol)
    else:
        return getattr(obj, 'company_name', obj.symbol)

@register.simple_tag
def get_type_badge(obj):
    """
    Get the appropriate type badge for a Stock or Index object
    """
    if obj._meta.model_name == 'index':
        return 'Index'
    else:
        return 'Stock'

@register.simple_tag
def get_type_icon(obj):
    """
    Get the appropriate icon for a Stock or Index object
    """
    if obj._meta.model_name == 'index':
        return 'fas fa-chart-line'
    else:
        return 'fas fa-building'

@register.simple_tag
def get_type_color(obj):
    """
    Get the appropriate color class for a Stock or Index object
    """
    if obj._meta.model_name == 'index':
        return 'text-info'
    else:
        return 'text-primary'
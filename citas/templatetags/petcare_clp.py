# PETCARE 165R.357.9.245C - FORMATO CLP

from django import template

register = template.Library()


@register.filter(name="precio_clp")
def precio_clp(valor):
    if valor is None or valor == "":
        return "Sin definir"

    try:
        numero = int(valor)
    except (TypeError, ValueError, OverflowError):
        return "Sin definir"

    return "$" + format(numero, ",d").replace(",", ".")

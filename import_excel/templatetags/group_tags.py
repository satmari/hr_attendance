from django import template

register = template.Library()

@register.filter
def has_group(user, group_name):
    return user.groups.filter(name=group_name).exists()

@register.filter
def hhmm(value):
    if not value:
        return "—"
    try:
        return value.strftime("%H:%M")
    except AttributeError:
        return "—"

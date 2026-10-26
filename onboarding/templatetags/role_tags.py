from django import template

from onboarding.permissions import is_hr

register = template.Library()


@register.simple_tag(takes_context=True)
def hr_account(context):
    return is_hr(context["user"])

from django.template.defaulttags import register

from package import models


@register.simple_tag(takes_context=True)
def country_code_to_name(context):
    request = context.get("request")
    try:
        country = models.Country.objects.filter(
            code=request.session.get('country')
        ).first()
        if country:
            return country.name
        else:
            return ''
    except models.Country.DoesNotExist:
        return request.session.get('country')

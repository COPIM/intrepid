from django import template

register = template.Library()
from accounts import models


@register.simple_tag
def is_current_banding_for_user(banding, vocab, request):
    """
    This checks whether or not this banding is currently set for the user
    :param request: the request object
    :return: true or false
    """
    try:
        models.AccountBandingChoices.objects.get(
            account=request.user,
            banding_type=banding,
            banding_type_vocab=vocab
        )
        return True
    except models.AccountBandingChoices.DoesNotExist:
        return False

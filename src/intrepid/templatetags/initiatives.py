from django import template

from initiatives import models

register = template.Library()


@register.simple_tag()
def user_is_initiative_manager(request, role) -> bool:
    """
    Check if the user is a manager of an initiative
    :param request: a request object
    :param role: a role object
    :return: true if the user is a manager of an initiative otherwise false
    """
    if models.Initiative.objects.filter(
        users=request.user,
    ).exists():
        return True

    return False

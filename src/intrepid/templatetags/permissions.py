from django import template

from fluid_permissions import models


register = template.Library()


@register.simple_tag(takes_context=True)
def user_has_fluid_permission(context, view_name) -> bool:
    """
    Check if the user has a permission to a view.
    :param context: the request context
    :param view_name: the view name
    :return: true if allowed to view, otherwise false
    """
    request = context.get("request")
    view_groups = models.ViewGroup.objects.filter(
        view_name=view_name,
        groups__in=request.user.groups.all(),
    )

    return view_groups.exists()

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from initiatives import models as im


def user_is_initiative_manager(func):
    """
    Checks that the current user is an initiative manager
    :param func: the function to wrap
    :return: the result of the underlying function
    """

    @login_required
    def wrapper(request, *args, **kwargs):
        """
        Checks that the current user is an initiative manager
        :param request: a Django request object
        :param args: args to pass to the underlying function
        :param kwargs: kwargs to pass to the underlying function
        :return: the result of the underlying function
        """

        # handle either initiative or initiative_id in the URL
        initiative_id = kwargs.get("initiative", None)
        id_suffix = False

        if not initiative_id:
            initiative_id = kwargs.get("initiative_id", None)
            id_suffix = True

        if initiative_id:
            initiative = get_object_or_404(
                im.Initiative,
                pk=initiative_id,
            )

            # patch the data into the kwargs
            if not id_suffix:
                kwargs["initiative"] = initiative
            else:
                kwargs["initiative_id"] = initiative.pk

            # only return the underlying function if the user is an initiative
            # manager
            if _is_initiative_manager(request, initiative):
                return func(request, *args, **kwargs)

        else:
            if _is_initiative_manager(request, None):
                return func(request, *args, **kwargs)

        # by default, raise a permission denied error
        raise PermissionDenied("You do not have permission to view this page.")

    return wrapper


def _is_initiative_manager(request, initiative) -> bool:
    """
    Checks that the current user is an initiative manager
    :param request: a request object
    :param initiative: an initiative object
    :return: True if the user is allowed to view the page, False otherwise
    """
    if request.user.is_staff or request.user.is_superuser:
        return True

    if initiative:
        if request.user in initiative.users.all():
            return True

    return False

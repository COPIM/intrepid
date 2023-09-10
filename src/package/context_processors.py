from package import models


def packages_awaiting_approval(request) -> dict[str, models.Package]:
    """
    Returns a dictionary of packages awaiting approval
    :param request: the request object (unused)
    :return: a dictionary of packages awaiting approval
    """

    return {
        "packages_awaiting_approval": models.Package.objects.filter(
            active=False,
        )
    }

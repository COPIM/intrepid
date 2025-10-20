from django import template

from cms import models


register = template.Library()


@register.simple_tag()
def conflict_statement(package, basket):
    """
    Returns a string describing the conflict between the package and the basket.
    :param package: the package to check for conflicts
    :param basket: the basket to check for conflicts
    :return: a string describing the conflict between the package and the basket
    """
    package_meta_packages = package.meta_packages()
    text = models.SiteText.objects.get(
        key='included_within_offers',
    )

    conflicting_metapackage_names = []
    for meta_package in package_meta_packages:
        if meta_package in basket.meta_packages.all():
            conflicting_metapackage_names.append(meta_package.name)

    return "{}: {}".format(
        text,
        ", ".join(conflicting_metapackage_names)
    )

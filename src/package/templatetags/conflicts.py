from django import template


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

    conflicting_metapackage_names = []
    for meta_package in package_meta_packages:
        if meta_package in basket.meta_packages.all():
            conflicting_metapackage_names.append(meta_package.name)

    return "Included within these offers: {}".format(
        ", ".join(conflicting_metapackage_names)
    )

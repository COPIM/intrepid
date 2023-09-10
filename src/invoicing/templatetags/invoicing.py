from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def order_invoices_processor(context, order):
    """
    Returns a queryset of invoices for the given order, filtered by the
    request user's payment processors.
    :param context: the request context
    :param order: the order to filter invoices for
    :return: a queryset of invoices
    """
    request = context.get("request")
    signups = order.packagesignup_set.all()

    if request.user.is_staff or request.user.is_superuser:
        pass
    else:
        # filter by payment processor
        to_remove = []

        for signup in signups:
            if (
                signup.payment_processor
                and not signup.payment_processor.is_member(request.user)
            ):
                # user is not a payment processor for this signup
                to_remove.append(signup)
            elif not signup.payment_processor:
                # this signup has no payment processor
                to_remove.append(signup)

        # exclude non-owned items from the queryset
        for remove in to_remove:
            signups = signups.exclude(pk=remove.pk)

    return signups

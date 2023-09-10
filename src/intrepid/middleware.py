from django.conf import settings

from initiatives import models as initiative_models
from intrepid import models as intrepid_models
from invoicing import models as invoice_models
from package import models as package_models
from thoth import models as thoth_models


def debug_middleware(get_response):
    """
    Middleware that prints the IP address of the request to the console
    :param get_response: a callable that takes a request and returns a response
    :return: a request object
    """

    def middleware(request):
        if settings.DEBUG:
            print(
                "IP Address for debug-toolbar: " + request.META["REMOTE_ADDR"]
            )

        return get_response(request)

    return middleware


def session_middleware(get_response):
    """
    Middleware that ensures that a session key is always present
    :param get_response: a callable
    :return: a request object
    """

    def middleware(request):
        if not request.session.session_key:
            request.session.save()

        return get_response(request)

    return middleware


def variables_middleware(get_response):
    """
    Middleware that injects commonly used variables into the request
    :param get_response: a callable
    :return: a new request object
    """

    def middleware(request):
        try:
            setup = intrepid_models.SiteSetup.objects.all().order_by("pk")[0]
        except IndexError:
            setup = intrepid_models.SiteSetup()
            setup.save()

        request.site_name = setup.site_name
        request.site = setup

        request.twitter_url = setup.twitter_url
        request.contact_email = setup.contact_email

        request.matomo_site_url = settings.MATOMO_SITE_URL
        request.matomo_site_id = settings.MATOMO_SITE_ID

        if hasattr(request, "user") and request.user.is_authenticated:
            # inject a document count into the request for the count on the
            # library dashboard
            request.document_count = package_models.Order.objects.filter(
                associated_user=request.user
            ).count()

            # inject a signup count into the request for the count on the
            # library dashboard

            # given that we have to do this anyway for the count, we might as
            # well store the full signup set so that we can reuse that in the
            # dashboard
            request.packages = (
                package_models.Package.objects.filter(
                    active=True, initiative__users__in=[request.user]
                )
                if request.user
                else []
            )

            packages = request.packages.values_list("pk", flat=True)

            request.signups = package_models.PackageSignup.objects.filter(
                associated_package__id__in=packages,
            ).order_by("-signup_date")

            request.new_signups = request.signups.filter(
                initiative_approved__isnull=True,
            )

            request.signup_count = request.signups.count()
            request.new_signup_count = request.new_signups.count()

            request.initiatives = initiative_models.Initiative.objects.filter(
                users__in=[request.user]
            )

            # active baskets
            request.active_baskets = request.user.basket_set.filter(active=True)

            # saved searches
            request.saved_searches = thoth_models.ThothSearch.objects.filter(
                user=request.user
            )

            if request.user.is_staff or request.user.is_superuser:
                payment_processors = (
                    invoice_models.PaymentProcessor.objects.all().distinct()
                )
                request.payment_processors = payment_processors
                request.is_payment_processor = True
            else:
                request.is_payment_processor = False

            if not request.is_payment_processor:
                # determine if user is a payment processor
                try:
                    payment_processors = (
                        invoice_models.PaymentProcessor.objects.filter(
                            managers__id=request.user.id
                        )
                    )

                    if payment_processors.count() > 0:
                        request.is_payment_processor = True
                        request.payment_processors = payment_processors

                except invoice_models.PaymentProcessor.DoesNotExist:
                    pass

        return get_response(request)

    return middleware

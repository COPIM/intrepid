from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.urls import reverse
from rest_framework import generics
from rest_framework import viewsets
from rest_framework.response import Response

from api import serializers
from initiatives import models as initiative_models
from package import models as package_models
from package.models import Basket  # adjust import to your app
from vocab import models as vocab_models

User = get_user_model()

class BasketSessionAPIView(generics.GenericAPIView):
    """
    Shows basket status for a session cookie ID
    """
    serializer_class = serializers.BasketSummarySerializer

    def get_basket_url(self, request):
        basket_path = reverse("basket_list")

        # Prefer explicit DOMAIN_NAME setting if present,
        # else use current request
        domain = getattr(settings, "DOMAIN_NAME", "openbookcollective.org")
        if domain:
            # Ensure no trailing slash duplication issues
            domain = domain.rstrip("/")
            return f"{domain}{basket_path}"
        return request.build_absolute_uri(basket_path)

    def get_basket_count(self, session_id, user):

        if not user:
            baskets = Basket.objects.filter(session_id=session_id, active=True)
        else:
            baskets = Basket.objects.filter(account=user, active=True)

        orders = 0

        for basket in baskets:
            orders_basket = basket.packages.count()
            orders += orders_basket

            meta_packages_basket = basket.meta_packages.count()
            orders += meta_packages_basket

        # set the basket
        if baskets.exists():
            basket = baskets.first()
        else:
            basket = None

        return orders, basket

    def get_user_from_session_key(self, session_key: str):
        """
        Given a Django session_key (sessionid cookie value),
        return a tuple: (session, user_or_None)
        """

        try:
            session = Session.objects.get(session_key=session_key)
        except Session.DoesNotExist:
            return None, None

        # The session is valid; decode it
        session_data = session.get_decoded()

        # Django stores the authenticated user's ID under this key
        uid = session_data.get('_auth_user_id')
        backend_path = session_data.get('_auth_user_backend')

        if not uid or not backend_path:
            return session, None

        try:
            user = User.objects.get(pk=uid)
        except User.DoesNotExist:
            return session, None

        return session, user

    def get(self, request, session_id, *args, **kwargs):
        session, user = self.get_user_from_session_key(session_id)

        orders, basket = self.get_basket_count(session_id, user)

        data = {
            "session_id": session_id,
            "basket": self.get_basket_url(request),
            "items": orders,
        }

        serializer = self.get_serializer(data)
        return Response(serializer.data)


class PackageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows packages to be viewed.
    """

    queryset = package_models.Package.objects.filter(active=True).order_by(
        "name"
    )
    serializer_class = serializers.PackageSerializer


class InitiativeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows initiatives to be viewed.
    """

    queryset = initiative_models.Initiative.objects.filter(
        active=True
    ).order_by("name")

    serializer_class = serializers.InitiativeSerializer


class StandardViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows standards to be viewed.
    """

    queryset = vocab_models.StandardVocab.objects.all()

    serializer_class = serializers.StandardSerializer


class PackageStandardAttestationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows standards to be viewed.
    """

    queryset = vocab_models.PackageStandardAttestation.objects.all()

    serializer_class = serializers.PackageStandardAttestationSerializer


class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows countries and currencies to be viewed.
    """

    queryset = package_models.Country.objects.all()

    serializer_class = serializers.CountrySerializer


class BandingTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows banding types to be viewed.
    """

    queryset = package_models.BandingType.objects.filter(active=True)

    serializer_class = serializers.BandingTypeSerializer


class BandingVocabViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows banding vocabularies to be viewed.
    """

    queryset = vocab_models.BandingVocab.objects.all()

    serializer_class = serializers.BandingVocabSerializer


class BandingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows bandings to be viewed.
    """

    queryset = package_models.Banding.objects.filter(active=True)

    serializer_class = serializers.BandingSerializer


class PriceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows prices to be viewed.
    """

    queryset = package_models.Price.objects.all()

    serializer_class = serializers.PriceSerializer

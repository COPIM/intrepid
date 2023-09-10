from rest_framework import viewsets

from api import serializers
from initiatives import models as initiative_models
from package import models as package_models
from vocab import models as vocab_models


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

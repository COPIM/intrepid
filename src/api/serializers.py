from rest_framework import serializers

from initiatives import models as initiative_models
from package import models as package_models
from vocab import models as vocab_models


class PackageSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = package_models.Package
        fields = [
            "name",
            "bandings",
            "description",
            "initiative",
            "standards_attested",
        ]


class InitiativeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = initiative_models.Initiative
        fields = ["name", "description", "packages"]


class StandardSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = vocab_models.StandardVocab
        fields = ["standard_name", "text"]


class PackageStandardAttestationSerializer(
    serializers.HyperlinkedModelSerializer
):
    class Meta:
        model = vocab_models.PackageStandardAttestation
        fields = ["standard", "details_url"]


class CountrySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = package_models.Country
        fields = ["name", "code", "currency", "prices"]


class BandingTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = package_models.BandingType
        fields = ["name", "is_fte", "vocabs"]


class BandingVocabSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = vocab_models.BandingVocab
        fields = ["text", "upper_limit", "lower_limit"]


class BandingSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = package_models.Banding
        fields = ["banding_type", "vocab", "prices"]


class PriceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = package_models.Price
        fields = ["banding", "country", "value"]

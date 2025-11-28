from django.urls import include, path
from rest_framework import routers

from api import views


class ApiRoot(routers.APIRootView):
    """
    The root API view for OBC.
    """

    pass


class DocumentedRouter(routers.DefaultRouter):
    APIRootView = ApiRoot


router = DocumentedRouter()
router.register(r"bandings", views.BandingViewSet)
router.register(r"banding_types", views.BandingTypeViewSet)
router.register(r"banding_vocabs", views.BandingVocabViewSet)
router.register(r"countries", views.CountryViewSet)
router.register(r"initiatives", views.InitiativeViewSet)
router.register(r"packages", views.PackageViewSet)
router.register(r"package_standards", views.PackageStandardAttestationViewSet)
router.register(r"prices", views.PriceViewSet)
router.register(r"standards", views.StandardViewSet)



# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path("", include(router.urls)),
    path(
        "api-auth/", include("rest_framework.urls", namespace="rest_framework")
    ),
    path("session/<str:session_id>/", views.BasketSessionAPIView.as_view(), name="basket_session"),
]

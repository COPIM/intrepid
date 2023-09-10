from django.urls import path

from summary import views

urlpatterns = [
    path(
        '<str:package_or_initiative>/<int:identifier>/summary/',
        views.summary_package_initiative,
        name='summary_package_initiative',
    ),
    path(
        '<str:package_or_initiative>/<int:identifier>/moreinfo/',
        views.summary_more_info,
        name='summary_more_info',
    ),
    path(
        '<str:package_or_initiative>/<int:identifier>/pricing/',
        views.summary_pricing,
        name='summary_pricing',
    ),
    path(
        'collections/<int:package_id>/',
        views.summary_meta_package,
        name='summary_meta_package',
    ),
]

from django.urls import path, include
from two_factor.urls import urlpatterns as tf_urls

from accounts import views as account_views

urlpatterns = [
    path("login/", account_views.login, name="login"),
    path("profile/", account_views.profile, name="profile"),
    path("profile/edit/", account_views.edit_profile, name="edit_profile"),
    path("account/", include("django.contrib.auth.urls")),
    path(
        "permissions/",
        account_views.manage_fluid_permissions,
        name="manage_fluid_permissions",
    ),
    path("manage/", account_views.manage_accounts, name="manage_accounts"),
    path("2fa/", include(tf_urls)),
    path(
        "bandings/",
        account_views.manage_account_bandings,
        name="manage_account_bandings",
    ),
    path("register/", account_views.register, name="register"),
    path(
        "activate/<uuid:activation_code>/",
        account_views.activate,
        name="activate",
    ),
]

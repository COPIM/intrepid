"""
Views for the document management portal.

The same screens serve both audiences; what differs is the data shown, which is
governed by the permission checks in ``portal.permissions``.
"""


def index(request):
    """Landing page: redirect to the OBC dashboard or the Provider list."""
    raise NotImplementedError

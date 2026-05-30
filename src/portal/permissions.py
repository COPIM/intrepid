"""
Permission helpers and decorators for the portal.

Two complementary layers protect every view:

* Layer A — per-Provider scoping for Provider Members, reusing the existing
  ``intrepid.security.user_is_initiative_manager`` decorator.
* Layer B — per-document-type read/write granularity for the OBC team, via the
  ``user_can`` helper and ``requires_doc_type`` decorator defined here.
"""


def is_obc_staff(user):
    """Return whether ``user`` is treated as full-access OBC staff."""
    raise NotImplementedError


def user_can(user, action, doc_type):
    """Return whether ``user`` may perform ``action`` on ``doc_type``."""
    raise NotImplementedError

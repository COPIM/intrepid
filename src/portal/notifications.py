"""
Notification queue/digest helpers.

A document upload enqueues one pending row per active contact; a 15-minute cron
job drains rows whose ``eligible_at`` has passed, grouping digest recipients
into a single email. Deleting a document cancels its unsent rows.
"""


def enqueue_for_document(document):
    """Enqueue notification rows for a newly-created document."""
    raise NotImplementedError


def cancel_for_document(document):
    """Cancel all unsent notification rows for a deleted document."""
    raise NotImplementedError


def send_pending_notifications():
    """Drain due notification rows, grouping digests. Returns count sent."""
    raise NotImplementedError

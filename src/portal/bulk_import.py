"""
Bulk-import pipeline: parse a ZIP whose folders follow the
``<short_code>/YYYY-MM/<anything>.<ext>`` convention into staged rows, then
commit those rows into ``Document`` records.
"""


def parse_zip(zip_path):
    """Parse a ZIP into staged bulk-import rows (dry run)."""
    raise NotImplementedError


def commit_job(job, notify_on_commit=False):
    """Create ``Document`` rows from a previously-staged job."""
    raise NotImplementedError

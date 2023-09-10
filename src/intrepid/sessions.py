from django.contrib.sessions.backends.db import SessionStore as DbSessionStore

from package import models


class SessionStore(DbSessionStore):
    """
    Extends the default session store to update the session ID for when
    a user logs in, to preserver their basket.
    """

    def cycle_key(self) -> None:
        """
        Cycles a key in the session store when the user logs in.
        :return: None
        """
        old_session_key = self.session_key
        super(SessionStore, self).cycle_key()
        new_session_key = self.session_key

        models.Basket.objects.filter(
            session_id=old_session_key,
        ).update(
            session_id=new_session_key,
        )

import os

from intrepid.settings import *  # noqa: F401, F403

MIGRATION_MODULES = {
    'fluid_permissions': 'test_migrations.fluid_permissions',
}

FIXTURE_DIRS = [
    os.path.join(BASE_DIR, '..', 'fixtures'),
]

# Disable HTTP Basic Auth for test client requests
BASICAUTH_DISABLE = True

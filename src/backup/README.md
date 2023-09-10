# Intrepid Backup System
The Intrepid backup system is controlled by the .backup.sh script that lives in the project's root directory. Further, there are a set of Django admin commands that allow for easy access to backups.

Backups are stored in a private S3 bucket, provisioned by Terraform, called "openbookcollectivebackup". Versioning retains backups for a year before discarding them.

[![asciicast](https://asciinema.org/a/HnqOncypouhiHcs4r2mZn0TRS.svg)](https://asciinema.org/a/HnqOncypouhiHcs4r2mZn0TRS)

## The Backup App
There are three commands provided by the backup app:

    src/manage.py push_backup    
    src/manage.py pull_backup
    src/manage.py list_backups

Each of these commands takes a different action with respect to saving, restoring, or listing backups.

### Setup
The app requires a few settings in the settings file:

    AWS_ACCESS_KEY_ID = 'AN_AWS_ACCESS_KEY_ID'
    AWS_SECRET_ACCESS_KEY = 'AN_AWS_SECRET_ACCESS_KEY'
    AWS_DEFAULT_REGION = 'eu-west-2'
    BACKUP_BUCKET = 'openbookcollectivebackup'

You can get the requisite details from Terraform, which manages this user. Run terraform apply and then terraform output --json to get the secret key details.

### Push Backup
This command pushes a backup to the server.

    usage: manage.py push_backup [-h] [--backup-local-file BACKUP_LOCAL_FILE] [--remote-key REMOTE_KEY] [--version] [-v {0,1,2,3}] [--settings SETTINGS] [--pythonpath PYTHONPATH] [--traceback] [--no-color] [--force-color]
                                 [--skip-checks]
    
    Pushes the backup SQL to the S3 store

Example usage:

    src/manage.py push_backup --backup-local-file=/home/obc/backups/data.json --remote-key=data.json

### Pull Backup
This command retrieves a backup file from the server. You must also specify the version you wish to retrieve.

    usage: manage.py pull_backup [-h] [--backup-version BACKUP_VERSION] [--out-file OUT_FILE] [--remote-key REMOTE_KEY] [--version] [-v {0,1,2,3}] [--settings SETTINGS] [--pythonpath PYTHONPATH] [--traceback] [--no-color]
                                 [--force-color] [--skip-checks]
    
    Pulls a specific backup SQL from the S3 store

Example:

    src/manage.py pull_backup --remote-key=data.json --backup-version=jB1dtbf1qraDQhBlKGGDXKAZugEnT2KB --out-file=/home/user/data.json

### List Backups
This command shows you available backups (usually for backup.tar.gz or data.json)

    usage: manage.py list_backups [-h] [--remote-key REMOTE_KEY] [--version] [-v {0,1,2,3}] [--settings SETTINGS] [--pythonpath PYTHONPATH] [--traceback] [--no-color] [--force-color] [--skip-checks]
    
    Lists available SQL backups

Example:

    src/manage.py list_backups --remote-key=data.json

# Restoring a Backup
Restoring a backup consists of the following steps. First, find the backups that you want:

    src/manage.py list_backups --remote-key=data.json
    src/manage.py list_backups --remote-key=backup.tar.gz

You can use grep to find a specific date.

Then pull the files down:

    src/manage.py pull_backup --remote-key=data.json --backup-version=<INSERT_BACKUP_VERSION_ID> --out-file=/home/obc/data.json
    src/manage.py pull_backup --remote-key=backup.tar.gz --backup-version=<INSERT_BACKUP_VERSION_ID> --out-file=/home/obc/backup.tar.gz

Untar backup.tar.gz ("tar -xzf backup.tar.gz") and replace /var/www/media and /home/obc/intrepid/src/files with the results.

Reload the database:

    /home/obc/intrepid-venv/bin/python3 /home/obc/intrepid/src/manage.py loaddata /home/obc/data.json

&copy; ΔQ Programming 2022.


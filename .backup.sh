#!/bin/bash
mkdir -p /home/obc/backups
/home/obc/intrepid-venv/bin/python3 /home/obc/intrepid/src/manage.py dumpdata > /home/obc/backups/data.json
/home/obc/intrepid-venv/bin/python3 /home/obc/intrepid/src/manage.py dumpdata thoth > /home/obc/backups/thoth.json
tar -czf /home/obc/backups/backup.tar.gz /var/www/media /home/obc/intrepid/src/files
/home/obc/intrepid-venv/bin/python3 /home/obc/intrepid/src/manage.py push_backup --backup-local-file=/home/obc/backups/data.json --remote-key=data.json
/home/obc/intrepid-venv/bin/python3 /home/obc/intrepid/src/manage.py push_backup --backup-local-file=/home/obc/backups/thoth.json --remote-key=thoth.json
/home/obc/intrepid-venv/bin/python3 /home/obc/intrepid/src/manage.py push_backup --backup-local-file=/home/obc/backups/backup.tar.gz --remote-key=backup.tar.gz

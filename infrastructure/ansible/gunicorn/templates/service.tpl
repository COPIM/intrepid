[Unit]
Description=gunicorn daemon
After=network.target

[Service]
User=obc
Group=obc
WorkingDirectory=/home/obc/intrepid/src
ExecStart=/home/obc/intrepid-venv/bin/gunicorn \
          --access-logfile - \
          --threads 3 \
          --workers 2 \
          --bind unix:/var/www/sockets/gunicorn.sock \
          intrepid.wsgi:application

[Install]
WantedBy=multi-user.target

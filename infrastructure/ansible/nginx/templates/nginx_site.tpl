server {
    server_name openbookcollective.org www.openbookcollective.org;

    location = /favicon.ico { access_log off; log_not_found off; alias /home/obc/intrepid/src/static/img/favicon.ico;}
    location /static/ {
        alias /var/www/static/;
    }

    location /media/ {
        alias /var/www/media/;
    }

    location / {
	proxy_pass http://unix:/var/www/sockets/gunicorn.sock;
        include proxy_params;
    }

    listen 80;

    client_max_body_size 250M;
}

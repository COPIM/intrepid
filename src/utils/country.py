import os

from django.conf import settings

import geoip2.database
from geoip2.errors import AddressNotFoundError


def get_ip_address(request):
    if request is None:
        return None

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_iso_country_code(request):
    ip = get_ip_address(request)
    db_path = os.path.join(
        settings.BASE_DIR,
        'utils',
        'geolite_country.mmdb',
    )
    reader = geoip2.database.Reader(db_path)

    try:
        response = reader.country(ip)
        return response.country.iso_code if response.country.iso_code else 'OTHER'
    except AddressNotFoundError:
        if ip == '127.0.0.1':
            return "GB"
        return 'OTHER'

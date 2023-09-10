import json

from django.http import HttpResponse


def json_response(func) -> callable:
    """
    A decorator that allows for JSONP callbacks
    :param func: The function to decorate
    :return: The decorated function
    """

    def decorator(request, *args, **kwargs) -> HttpResponse:
        objects = func(request, *args, **kwargs)
        if isinstance(objects, HttpResponse):
            return objects
        try:
            data = json.dumps(objects)

            if "callback" in request.GET:
                # a jsonp response!
                data = "%s(%s);" % (request.GET["callback"], data)
                return HttpResponse(data, "text/javascript")
        except:
            data = json.dumps(str(objects))
        return HttpResponse(data, "application/json")

    return decorator

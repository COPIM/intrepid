from django.contrib.auth.models import Group

from fluid_permissions import models


def process_permission_change(request):
    permission_post = request.POST.getlist("permissions[]")
    permission_update = dict()

    for vg in models.ViewGroup.objects.all():
        permission_update[str(vg.pk)] = []

    for permission in permission_post:
        view_group_pk, group_pk = permission.split("-")
        permission_update[view_group_pk].append(group_pk)

    for k, v in permission_update.items():
        view_group = models.ViewGroup.objects.get(
            pk=k,
        )
        view_group.groups.clear()
        groups = Group.objects.filter(pk__in=v)
        view_group.groups.add(*groups)

import os
from inspect import getsourcefile
from os.path import abspath

import crontab
from crontab import CronTab
from django.conf import settings
from django.core.management.base import BaseCommand


def find_job(tab, comment) -> crontab.CronItem | None:
    """
    Find job in cron tab
    :param tab: the cron tab
    :param comment: the comment
    :return: the job or None
    """
    for job in tab:
        if job.comment == comment:
            return job
    return None


class Command(BaseCommand):
    """
    Installs cron tasks.
    """

    help = "Installs cron tasks."

    def add_arguments(self, parser):
        parser.add_argument("--action", default="")

    def handle(self, *args, **options):
        """Installs Cron

        :param args: None
        :param options: None
        :return: None
        """
        action = options.get("action")
        tab = CronTab(user=True)
        virtualenv = os.environ.get("VIRTUAL_ENV", None)

        cwd = abspath(getsourcefile(lambda: 0) + "/../../../../")
        cwd = cwd.replace("/", "_")

        jobs = [
            {
                "name": "{}_intrepid_sync_thoth_job".format(cwd),
                "time": -1,
                "day": 1,
                "task": "sync_thoth",
            },
        ]

        for job in jobs:
            current_job = find_job(tab, job["name"])

            if not current_job:
                django_command = "{0}/manage.py {1}".format(
                    settings.BASE_DIR, job["task"]
                )
                if virtualenv:
                    command = "%s/bin/python3 %s" % (virtualenv, django_command)
                else:
                    command = "%s" % django_command

                cron_job = tab.new(command, comment=job["name"])
                if job["time"] != -1:
                    cron_job.minute.every(job["time"])
                else:
                    cron_job.setall("0 1 * * *")

            else:
                print(
                    "{name} cron job already exists.".format(name=job["name"])
                )

        if action == "test":
            print(tab.render())
        elif action == "quiet":
            pass
        else:
            tab.write()

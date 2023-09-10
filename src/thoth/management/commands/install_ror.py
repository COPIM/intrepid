"""
(c) ΔQ Programming LLP, 2021
This program is free software; you may redistribute and/or modify
it under the terms of the Apache License v2.0.
"""
import io
import json
import tempfile
import zipfile
from contextlib import closing

import requests
from django.core.management.base import BaseCommand
from django.db import transaction
from tqdm import tqdm

from thoth.models import RORRecord


class Command(BaseCommand):
    """
    A management command that fetches and installs the latest ROR support
    """

    help = "Installs ROR functionality into Thoth components"

    @transaction.atomic
    def handle(self, *args, **options):
        # download the latest ROR file from Zenodo
        url = (
            "https://zenodo.org/api/records/"
            "?communities=ror-data&sort=mostrecent"
        )

        # the meta response is the JSON from Zenodo that specifies the latest
        # version
        meta_response = requests.get(url)
        latest_url = meta_response.json()["hits"]["hits"][0]["files"][0][
            "links"
        ]["self"]

        # this downloads and unzips the latest ROR file to a temp JSON file
        # when this context processor closes, the temporary files will be
        # deleted
        print("Downloading ROR records")
        with tempfile.NamedTemporaryFile(suffix=".json") as f:
            zip_file = requests.get(latest_url)

            print("Extracting ROR JSON")

            with closing(zip_file), zipfile.ZipFile(
                io.BytesIO(zip_file.content)
            ) as archive:
                f.write(archive.read(archive.infolist()[0]))

            # now we have the JSON file at f
            f.seek(0)
            ror_json = json.loads(f.read())

        # delete existing records
        print("Deleting existing records")
        RORRecord.objects.all().delete()

        print("Importing")
        # Parse ROR JSON
        with tqdm(total=len(ror_json), unit="insts") as pbar:
            for entry in ror_json:
                ror_id = entry["id"]
                ror_name = entry["name"]
                ror_country = entry["country"]["country_code"]
                try:
                    grid_id = entry["external_ids"]["GRID"]["preferred"]
                except:
                    grid_id = None

                ror_record = RORRecord(
                    ror_id=ror_id,
                    institution_name=ror_name,
                    country=ror_country,
                    grid_id=grid_id,
                )
                ror_record.save()
                pbar.update(1)

        print(
            "ROR fixtures installed. At next Thoth sync, ROR functionality "
            "will be enabled."
        )

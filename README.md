# Intrepid

## About

Intrepid is a web application for managing initiatives, packages and metapackes.

## Getting Started

We recommend you use Docker to run Intrepid locally.

- Ensure you have make and docker installed.
- Navigate to the root folder of intrepid.
- Run `make install`.
- Once that process is complete you can use `make run` to run the application.
- Navigate to: `localhost:8000`.

## BIC, THEMA, and BISAC Codes
For Thoth integration with BIC, download a copy of the BIC "subjects only" XLS file, convert it to CSV and place it in the Thoth/fixtures directory as "BIC.csv" and the qualifications file as "BICQuals.csv". Then run the management command "install_bic".

For Thoth integration with Thema, download a copy of the Thema "categories and codes" XLS file, convert it to CSV and place it in the Thoth/fixtures directory as "thema.csv". Then run the management command "install_thema".

For Thoth integration with BISAC, download a copy of the Thema "Mapping from BISAC 2020 to Thema v1.4 codes (Excel)" file and convert it to CSV. Place it in the Thoth/fixtures directory as "bisac.csv". Then run the management command "install_bisac".

## Fluid Permissions
Intrepid makes use of Fluid Permissions that lets you pair a view with a group and then users in that group are authorised to access the given view. When adding new viewgroups you can regenerate the fixture with the following command:

`python3 src/manage.py dumpdata fluid_permissions.viewgroup --indent=4 --natural-foreign --natural-primary > fixtures/viewgroups.json`

# Two-Factor Authentication
2FA is supported via the django-twofactor app. The 2FA app uses the Sites framework to ascertain the issuer name in the app. To set this, fire up the django shell and run:

    from django.contrib.sites.models import Site
    one = Site.objects.all()[0]
    one.name = 'Open Book Collective'
    one.save()

# Model Translations
This is current a WIP. Here are instructions for setting up model translations.

## Models
Limited, currently, to the SiteText model. This will need to be expanded to cover all texts that appear on the front end.

## Languages
Initially I've enabled English and German, this can be extended in the future.

## Fallback
English is the designated fallback language, it will display when a user has not specified another language. Text must also be inserted in English before other languanges.

## Setup
To setup model translations follow these instructions:

### Settings
Add the following to settings.py

```python

INSTALLED_APPS = [
    'modeltranslation',
    ...
]

# LANGUAGES
LANGUAGE_CODE = 'en'
USE_I18N = True
gettext = lambda s: s
LANGUAGES = (
    ('de', gettext('German')),
    ('en', gettext('English')),
)
MODELTRANSLATION_DEFAULT_LANGUAGE = 'en'
MODELTRANSLATION_LANGUAGES = ('en', 'de')
MODELTRANSLATION_FALLBACK_LANGUAGES = ('en',)
MODELTRANSLATION_PREPOPULATE_LANGUAGE = 'en'
```

### Migrations
Once this is added to your settings.py run the following:

```shell
python3 src/manage.py migrate
python src/manage.py update_translation_fields
```

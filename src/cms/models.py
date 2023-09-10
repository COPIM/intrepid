from django.contrib.auth.models import User
from django.db import models
from django.shortcuts import reverse
from django.utils import timezone
from django_bleach.models import BleachField

from accounts.models import profile_images_upload_path
from initiatives.models import Initiative


class Version(models.Model):
    """
    A version of a page or news update. A page or news update can have
    """

    first_paragraph = BleachField(
        help_text="The first paragraph of the page, HTML. Do NOT start this "
        "paragraph with a link.",
        default="",
        allowed_tags=[
            "a",
            "br",
            "p",
            "em",
            "h1",
            "h2",
            "h3",
            "i",
            "b",
            "ul",
            "li",
            "ol",
        ],
    )

    pre_break_content = BleachField(
        help_text="A second paragraph that will be displayed before the image "
        "break. We recommend beginning this with a heading tag.",
        default="",
        allowed_tags=[
            "a",
            "br",
            "p",
            "em",
            "h1",
            "h2",
            "h3",
            "i",
            "b",
            "ul",
            "li",
            "ol",
        ],
        blank=True,
        null=True,
    )

    pull_quote = models.TextField(
        help_text="The text to display in the pull-quote",
        default="",
        blank=True,
        null=True,
    )

    show_quote_icons = models.BooleanField(default=True)

    body = BleachField(
        help_text="The rest of the page or news update, HTML. We recommend "
        "beginning this with a heading tag.",
        default="",
        allowed_tags=[
            "a",
            "br",
            "p",
            "em",
            "h1",
            "h2",
            "h3",
            "i",
            "b",
            "ul",
            "li",
            "ol",
        ],
    )
    created = models.DateTimeField(
        default=timezone.now,
    )
    created_by = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        ordering = ("-created",)

    def __str__(self):
        return "{} created on {} created by {}".format(
            self.pk, self.created, self.created_by
        )


class PageUpdate(models.Model):
    """
    A page or news update. A page or news update can have multiple versions.
    """

    target_institution = models.ForeignKey(
        "thoth.RORRecord",
        blank=True,
        null=True,
        verbose_name="Whether this update is visible only to people at a "
        "specific university",
        default=None,
        on_delete=models.CASCADE,
    )
    notification_sent = models.BooleanField(
        default=False,
        help_text="Used to block multiple Update notification sends.",
    )
    is_update = models.BooleanField(default=False)
    initiative = models.ForeignKey(
        "initiatives.Initiative",
        on_delete=models.CASCADE,
        null=True,
    )
    title = models.CharField(
        max_length=255,
        help_text="Text displayed in h1 for this page.",
    )
    created = models.DateTimeField(
        default=timezone.now,
    )
    updated_by = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_related",
        related_query_name="%(app_label)s_%(class)ss",
    )
    current_version = models.ForeignKey(
        Version,
        null=True,
        on_delete=models.SET_NULL,
        related_name="current_version",
    )
    display = models.BooleanField(
        default=False,
        verbose_name="Display",
        help_text="Check to make this live.",
    )
    other_versions = models.ManyToManyField(
        Version,
        blank=True,
    )
    sequence = models.PositiveIntegerField(
        default=99,
        help_text="Used to determine page order. Pages with the same sequence "
        "and then ordered by title.",
    )

    # page thumbnail that resizes to 510 x 302
    thumbnail_image = models.ImageField(
        verbose_name="Page Thumbnail (510x302)",
        upload_to=profile_images_upload_path,
        blank=True,
        null=True,
    )

    # page thumbnail that resizes to 1250x500
    mid_page_image = models.ImageField(
        verbose_name="Mid-Page Banner Image (1250x500)",
        upload_to=profile_images_upload_path,
        blank=True,
        null=True,
        default=None,
    )

    # a paragraph for the abstract
    abstract_paragraph = models.TextField(
        verbose_name="Page abstract " "paragraph (a " "brief summary)",
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.title

    class Meta:
        ordering = ("sequence", "title")

    @property
    def first_character(self):
        """
        Returns the first character of the first paragraph of the current object
        :return: str
        """
        if (
            self.current_version.first_paragraph
            and len(self.current_version.first_paragraph) > 0
        ):
            if self.current_version.first_paragraph.startswith("<p>"):
                return self.current_version.first_paragraph[3]

            if self.current_version.first_paragraph.startswith("<span"):
                return self.current_version.first_paragraph[6]

            if self.current_version.first_paragraph.startswith("<"):
                found_index = self.current_version.first_paragraph.find(">")
                return self.current_version.first_paragraph[found_index + 1]

            return self.current_version.first_paragraph[0]

    @property
    def first_paragraph_minus_first_character(self):
        """
        Returns the first paragraph of the current object minus the first
        character
        :return: str
        """
        if (
            self.current_version.first_paragraph
            and len(self.current_version.first_paragraph) > 0
        ):
            # we can use linebreaks or paragraph breaks
            if "<p>" in self.current_version.first_paragraph:
                first_para = self.current_version.first_paragraph[4:]
                if first_para.endswith("</p>"):
                    first_para = first_para[:-4]
            else:
                first_para = self.current_version.first_paragraph[1:]
        else:
            first_para = ""

        return first_para

    @property
    def edit_url(self):
        """
        Returns the url for editing this page
        :return:
        """
        page_or_update = "update" if self.is_update else "page"
        return reverse(
            "page_edit",
            kwargs={
                "initiative": self.initiative.pk,
                "page_or_update": page_or_update,
                "page_id": self.pk,
            },
        )

    @property
    def detail_url(self) -> str:
        """
        Returns the url for viewing this page
        :return: an url string
        """
        page_or_update = "update" if self.is_update else "page"
        return reverse(
            "page_detail",
            kwargs={
                "initiative": self.initiative.pk,
                "page_or_update": page_or_update,
                "page_id": self.pk,
            },
        )


class WhoWeAreProfileItem(models.Model):
    """
    Configures items visible on the Who We Are page
    """

    # Note: technically, we could make this infinitely extensible by allowing
    # staff to add sections etc. (it is, after all, just a string)
    # But that's beyond scope for v1.0
    display_name = models.CharField(max_length=255)
    affiliation_line = models.CharField(max_length=255, blank=True, null=True)
    police_mugshot = models.ImageField(
        verbose_name="Profile image",
        upload_to=profile_images_upload_path,
        blank=True,
        null=True,
    )
    section = models.CharField(max_length=255)
    order = models.IntegerField(default=0)
    bio = models.TextField(blank=True, null=True)


class SiteWideNewsItem(models.Model):
    """
    Configures items visible on the site-wide news feed
    """

    update_item = models.ForeignKey(PageUpdate, on_delete=models.CASCADE)
    order = models.IntegerField(default=0)


class PrimaryInitiative(models.Model):
    """
    Configures the primary initiative for the site
    """

    initiative = models.ForeignKey(Initiative, on_delete=models.CASCADE)
    terms_page = models.ForeignKey(
        PageUpdate,
        on_delete=models.CASCADE,
        related_name="terms",
        blank=True,
        null=True,
    )
    documentation_page = models.ForeignKey(
        PageUpdate,
        on_delete=models.CASCADE,
        related_name="documentation",
        blank=True,
        null=True,
    )
    what_we_do_page = models.ForeignKey(
        PageUpdate,
        on_delete=models.CASCADE,
        related_name="what_we_do",
        blank=True,
        null=True,
    )
    values_page = models.ForeignKey(
        PageUpdate,
        on_delete=models.CASCADE,
        related_name="values",
        blank=True,
        null=True,
    )
    why_support_oa_page = models.ForeignKey(
        PageUpdate,
        on_delete=models.CASCADE,
        related_name="why_support_oa",
        blank=True,
        null=True,
    )
    governance_page = models.ForeignKey(
        PageUpdate,
        on_delete=models.CASCADE,
        related_name="governance",
        blank=True,
        null=True,
    )
    privacy_page = models.ForeignKey(
        PageUpdate,
        on_delete=models.CASCADE,
        related_name="privacy",
        blank=True,
        null=True,
    )
    accessibility_page = models.ForeignKey(
        PageUpdate,
        on_delete=models.CASCADE,
        related_name="accessibility",
        blank=True,
        null=True,
    )
    funding_model_page = models.ForeignKey(
        PageUpdate,
        on_delete=models.CASCADE,
        related_name="funding_model",
        blank=True,
        null=True,
    )

    supporters_page = models.ForeignKey(
        PageUpdate,
        on_delete=models.CASCADE,
        related_name="supporters",
        blank=True,
        null=True,
    )

    transforming_publishing_page = models.ForeignKey(
        PageUpdate,
        on_delete=models.CASCADE,
        related_name="transforming_publishing",
        blank=True,
        null=True,
        default=None,
    )

    supporting_libraries_page = models.ForeignKey(
        PageUpdate,
        on_delete=models.CASCADE,
        related_name="supporting_libraries",
        blank=True,
        null=True,
        default=None,
    )


class HomePageQuote(models.Model):
    """
    Configures quotes visible on the home page
    """

    pill_name = models.CharField(max_length=255, blank=True, null=True)
    quotation = models.TextField(max_length=255, blank=True, null=True)
    person_attribution = models.CharField(max_length=255, blank=True, null=True)
    organization_attribution = models.CharField(
        max_length=255, blank=True, null=True
    )
    order = models.IntegerField(default=0)

    organization_logo = models.ImageField(
        verbose_name="Associated quote image (145 x 145)",
        upload_to=profile_images_upload_path,
        blank=True,
        null=True,
    )


class FeaturedBook(models.Model):
    """
    Configures items visible on the home page
    """

    initiative = models.ForeignKey(
        "initiatives.Initiative", on_delete=models.CASCADE
    )
    book = models.ForeignKey("thoth.Work", on_delete=models.CASCADE)
    order = models.IntegerField(default=0)

    def __str__(self):
        return self.book.full_title


class SiteText(models.Model):
    """
    A site text object
    """

    key = models.SlugField(max_length=20, unique=True)
    body = models.TextField()
    help_text = models.TextField()
    rich_text = models.BooleanField(default=False)

    def __str__(self):
        return self.key

    def display(self, context) -> str:
        """
        Display the text, with an edit link if the user is staff
        :param context: the request context
        :return: the text, with an edit link if the user is staff
        """
        request = context.get("request")
        if not request.user or not request.user.is_staff:
            return self.body
        elif request.user and request.user.is_staff:
            url = reverse(
                "edit_site_text",
                kwargs={"key": self.key},
            )
            body = (
                '<a target="_blank" class="edit-button" href="{url}">'
                "Edit Text</a><br />{body}".format(url=url, body=self.body)
            )
            return body

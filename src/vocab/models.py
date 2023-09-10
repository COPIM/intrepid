from django.db import models
from django.utils import timezone


class StandardVocab(models.Model):
    """
    A standard to which a package can attest compliance
    """

    standard_name = models.CharField(max_length=255)

    text = models.TextField(
        help_text="The text of the attested standard.",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("standard_name",)

    def __str__(self) -> str:
        return self.standard_name

    def pk_str(self) -> str:
        """
        Returns the pk as a string
        :return: str
        """
        return str(self.pk)


class PackageStandardAttestation(models.Model):
    """
    An attestation of compliance with a standard
    """

    standard = models.ForeignKey(StandardVocab, on_delete=models.CASCADE)
    package = models.ForeignKey(
        "package.Package",
        on_delete=models.CASCADE,
        related_name="standards_attested",
        verbose_name="Standards to which this package attests",
    )
    details_url = models.URLField(
        blank=True,
        null=True,
        verbose_name="The URL detailing your implementation of this policy",
    )

    class Meta:
        ordering = ("standard__standard_name",)

    def __str__(self) -> str:
        return "{} {}".format(
            self.standard.standard_name,
            self.package.name,
        )


class AttestationHistory(models.Model):
    standard = models.ForeignKey(StandardVocab, on_delete=models.CASCADE)
    package = models.ForeignKey(
        "package.Package",
        on_delete=models.CASCADE,
    )
    add_or_remove = models.CharField(
        max_length=10,
        choices=(
            ("added", "Added"),
            ("removed", "Removed"),
        ),
    )
    date_time = models.DateTimeField(
        default=timezone.now,
    )

    class Meta:
        ordering = ("-date_time",)
        verbose_name_plural = "Attestation histories"


class BandingVocab(models.Model):
    """
    A standardised vocabulary option for package banding. E.g. "Jisc Band 1"
    """

    lower_limit = models.IntegerField(
        help_text="Lower limit of banding size eg 1000",
        blank=True,
        null=True,
    )
    upper_limit = models.IntegerField(
        help_text="Upper limit of banding size eg 10000.", blank=True, null=True
    )
    text = models.CharField(
        help_text="For non-fte banding types add the text here.",
        blank=True,
        null=True,
        max_length=255,
    )
    order = models.PositiveIntegerField(
        default=99,
    )

    class Meta:
        ordering = ("order",)

    def __str__(self) -> str:
        text = " ({})".format(self.text)
        if (self.lower_limit or self.lower_limit == 0) and self.upper_limit:
            return "{} - {} FTE{}".format(
                self.lower_limit, self.upper_limit, text if self.text else ""
            )
        elif (
            self.lower_limit or self.lower_limit == 0
        ) and not self.upper_limit:
            return "{} + FTE{}".format(
                self.lower_limit, text if self.text else ""
            )
        else:
            return self.text

    @property
    def is_fte(self) -> bool:
        """
        Returns true if the banding is fte
        :return: bool
        """
        if self.lower_limit or self.upper_limit and not self.text:
            return True
        else:
            return False

    def m2m_display(self) -> str:
        """
        Returns a string for the m2m display
        :return: str
        """
        if self.is_fte:
            return "{} - {} FTE".format(self.lower_limit, self.upper_limit)
        else:
            return self.text


class SubjectVocab(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name

    def subject_pk_str(self) -> str:
        """
        Returns the pk as a string
        :return: str
        """
        return str(self.pk)

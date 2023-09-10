from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class PaymentProcessor(models.Model):
    """
    A payment processor is a company that handles payments for us.
    """

    name = models.CharField(
        max_length=255,
    )
    notes = models.TextField(
        blank=True,
        null=True,
    )
    managers = models.ManyToManyField(
        User,
        blank=True,
    )
    countries = models.ManyToManyField(
        "package.Country",
        help_text="Countries covered by this payment processor.",
    )

    def __str__(self):
        return self.name

    def is_member(self, user):
        return user in self.managers.all()


def status_choices():
    """
    Choices for the status field of invoices.
    :return: a tuple of tuples
    """
    return (
        ("new", "New"),
        ("sent", "Invoice Sent"),
        ("paid", "Invoice Paid"),
    )


class SignupInvoice(models.Model):
    """
    An invoice for a signup.
    """

    payment_processor = models.ForeignKey(
        "PaymentProcessor",
        on_delete=models.CASCADE,
        null=True,
    )
    signup = models.OneToOneField(
        "package.PackageSignup",
        on_delete=models.CASCADE,
    )
    status = models.CharField(
        max_length=4,
        choices=status_choices(),
        default="new",
    )

    def __str__(self):
        return "Invoice for signup {}".format(
            self.signup.pk,
        )

    def last_status_update(self):
        """
        Get the last status update for this invoice.
        :return: an InvoiceLog object
        """
        return self.invoicelog_set.all().first()


class InvoiceLog(models.Model):
    """
    A log of status changes for an invoice.
    """

    invoice = models.ForeignKey(
        "SignupInvoice",
        on_delete=models.CASCADE,
    )
    status = models.CharField(
        max_length=4,
        choices=status_choices(),
        default="new",
    )
    date_time = models.DateTimeField(
        default=timezone.now,
    )

    class Meta:
        ordering = ("-date_time",)

    def __str__(self):
        return "Invoice Log for {}: {}".format(
            self.invoice.pk, self.get_status_display()
        )

from django.dispatch import receiver
from package import models, signals


@receiver(signals.price_cleanup_required)
def cleanup_prices(sender, **kwargs) -> None:
    """
    A signal receiver that runs the price garbage collector
    :param sender: the sender of the signal
    :param kwargs: the keyword arguments
    :return: None
    """
    # TODO: confirm whether this is still required

    print("Running price garbage collector")
    models.Price.collect()

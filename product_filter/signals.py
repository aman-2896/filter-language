from django.dispatch import Signal, receiver


health_checked = Signal()


@receiver(health_checked)
def on_health_checked(sender, **kwargs):
    print("Signal fired: health check was hit")
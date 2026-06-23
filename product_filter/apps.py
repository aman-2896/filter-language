from django.apps import AppConfig


class ProductFilterConfig(AppConfig):
    name = 'product_filter'
    def ready(self):
            import product_filter.signals


            
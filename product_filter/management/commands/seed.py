from django.core.management.base import BaseCommand
from product_filter.models import Product

class Command(BaseCommand):
    help = "Seed the database with sample products"

    def handle(self, *args, **options):
        Product.objects.all().delete()      # clean slate, so re-running is safe
        Product.objects.bulk_create([
            Product(name="single wall cup", price=120, color="white", category="cups", qty_available=600, tier=1, discontinued=False),
            Product(name="double wall cup", price=80,  color="kraft", category="cups", qty_available=300, tier=2, discontinued=False),
            Product(name="flat lid",        price=40,  color="white", category="lids", qty_available=900, tier=3, discontinued=True),
            Product(name="dome lid",        price=200, color="black", category="lids", qty_available=150, tier=1, discontinued=False),
        ])
        self.stdout.write(self.style.SUCCESS("Seeded 4 products"))
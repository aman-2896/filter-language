from django.urls import path
from product_filter.views import filter_products

urlpatterns=[
    path('filter/',filter_products)
]
from django.urls import path
from product_filter.views import filter_products,health_check

urlpatterns=[
    path('filter/',filter_products),
    path('health/', health_check),
]
from django.urls import path
from product_filter.views import filter_products,use_signals

urlpatterns=[
    path('v1/filter/',filter_products),
    path('/use-signals',use_signals)
]
from django.urls import path
from django.conf.urls import url
from . import views

urlpatterns = [
    path('', views.StockListView.as_view(), name='inventory'),
    path('new', views.StockCreateView.as_view(), name='new-stock'),
    path('stock/<pk>/edit', views.StockUpdateView.as_view(), name='edit-stock'),
    path('stock/<pk>/delete', views.StockDeleteView.as_view(), name='delete-stock'),
    path('stock/<pk>/guard-delete', views.StockDeleteView.as_view(), name='guard_delete'),
    path('stock/<pk>/restore', views.RestoreStockView.as_view(), name='restore-stock'),
]

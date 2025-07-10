from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('stock/<int:stock_id>/', views.stock_detail, name='stock_detail'),
    path('index/<int:index_id>/', views.index_detail, name='index_detail'),
    path('search/', views.search_stocks, name='search_stocks'),
    path('stock/<int:stock_id>/refresh/', views.refresh_stock_data, name='refresh_stock_data'),
    
    # AJAX endpoints
    path('api/stock/<int:stock_id>/quote/', views.get_live_quote, name='get_live_quote'),
    path('api/stock/<int:stock_id>/ohlc/', views.get_ohlc_data, name='get_ohlc_data'),
    path('api/stock/<int:stock_id>/refresh/', views.refresh_data_async, name='refresh_data_async'),
    path('api/index/<int:index_id>/refresh/', views.refresh_index_data_async, name='refresh_index_data_async'),
]
from django.contrib import admin
from .models import Stock, OHLCData, UserSession, LiveQuote

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'token', 'exchange', 'company_name', 'created_at']
    list_filter = ['exchange', 'created_at']
    search_fields = ['symbol', 'company_name', 'token']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(OHLCData)
class OHLCDataAdmin(admin.ModelAdmin):
    list_display = ['stock', 'timestamp', 'open_price', 'high_price', 'low_price', 'close_price', 'interval']
    list_filter = ['stock', 'interval', 'timestamp']
    search_fields = ['stock__symbol']
    readonly_fields = ['created_at']
    date_hierarchy = 'timestamp'

@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'is_active', 'created_at', 'expires_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['user_id']
    readonly_fields = ['created_at']

@admin.register(LiveQuote)
class LiveQuoteAdmin(admin.ModelAdmin):
    list_display = ['stock', 'ltp', 'change', 'change_percent', 'timestamp']
    list_filter = ['stock', 'timestamp']
    search_fields = ['stock__symbol']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'

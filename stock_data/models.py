from django.db import models
from django.utils import timezone

class Stock(models.Model):
    """Model to store stock information"""
    symbol = models.CharField(max_length=50, unique=True)
    token = models.CharField(max_length=20, unique=True)
    exchange = models.CharField(max_length=10, default='NSE')
    company_name = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.symbol} ({self.token})"
    
    class Meta:
        verbose_name = "Stock"
        verbose_name_plural = "Stocks"
        ordering = ['symbol']

class OHLCData(models.Model):
    """Model to store OHLC (Open, High, Low, Close) data"""
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='ohlc_data')
    timestamp = models.DateTimeField()
    open_price = models.DecimalField(max_digits=10, decimal_places=2)
    high_price = models.DecimalField(max_digits=10, decimal_places=2)
    low_price = models.DecimalField(max_digits=10, decimal_places=2)
    close_price = models.DecimalField(max_digits=10, decimal_places=2)
    volume = models.BigIntegerField(default=0)
    interval = models.IntegerField(default=5)  # Interval in minutes
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.stock.symbol} - {self.timestamp} ({self.interval}min)"
    
    class Meta:
        verbose_name = "OHLC Data"
        verbose_name_plural = "OHLC Data"
        ordering = ['-timestamp']
        unique_together = ['stock', 'timestamp', 'interval']

class UserSession(models.Model):
    """Model to store API session information"""
    user_id = models.CharField(max_length=50, unique=True)
    token = models.TextField()
    session_key = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    def __str__(self):
        return f"{self.user_id} - {'Active' if self.is_active else 'Inactive'}"
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    class Meta:
        verbose_name = "User Session"
        verbose_name_plural = "User Sessions"
        ordering = ['-created_at']

class LiveQuote(models.Model):
    """Model to store live stock quotes"""
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='live_quotes')
    ltp = models.DecimalField(max_digits=10, decimal_places=2)  # Last Traded Price
    open_price = models.DecimalField(max_digits=10, decimal_places=2)
    high_price = models.DecimalField(max_digits=10, decimal_places=2)
    low_price = models.DecimalField(max_digits=10, decimal_places=2)
    volume = models.BigIntegerField(default=0)
    change = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    change_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.stock.symbol} - ₹{self.ltp}"
    
    class Meta:
        verbose_name = "Live Quote"
        verbose_name_plural = "Live Quotes"
        ordering = ['-timestamp']

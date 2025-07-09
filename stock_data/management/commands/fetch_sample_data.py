"""
Django management command to fetch fresh sample data for testing
"""

from django.core.management.base import BaseCommand
from stock_data.services import FlattradeService

class Command(BaseCommand):
    help = 'Fetch fresh sample data from Flattrade API'

    def handle(self, *args, **options):
        self.stdout.write("🚀 Fetching fresh sample data...")
        
        service = FlattradeService()
        
        if not service.client or not service.client.is_connected:
            self.stdout.write(self.style.ERROR("❌ Failed to connect to Flattrade API"))
            return
        
        # Fetch live quote for Reliance
        self.stdout.write("📈 Fetching live quote for Reliance...")
        quote = service.get_live_quote('RELIANCE-EQ')
        if quote:
            self.stdout.write(self.style.SUCCESS(f"✅ Live quote: ₹{quote.ltp}"))
        
        # Fetch OHLC data for Reliance
        self.stdout.write("📊 Fetching OHLC data for Reliance...")
        ohlc_data = service.get_ohlc_data('RELIANCE-EQ')
        if ohlc_data:
            self.stdout.write(self.style.SUCCESS(f"✅ OHLC data: {len(ohlc_data)} new records"))
        
        self.stdout.write(self.style.SUCCESS("✅ Sample data fetch completed!"))
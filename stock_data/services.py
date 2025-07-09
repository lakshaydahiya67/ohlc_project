"""
Django services for Flattrade API integration
"""

import sys
import os
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from django.conf import settings

# Add the project root to Python path to import flattrade_client
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flattrade_client import FlattradeClient
from credentials import USER_ID, TOKEN
from .models import Stock, OHLCData, UserSession, LiveQuote

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class FlattradeService:
    """Service class for handling Flattrade API operations"""
    
    def __init__(self):
        self.client = None
        self.user_id = USER_ID
        self.token = TOKEN
        self.setup_client()
    
    def setup_client(self):
        """Initialize and authenticate Flattrade client"""
        try:
            logger.info(f"🔄 Setting up Flattrade client for user: {self.user_id}")
            self.client = FlattradeClient(self.user_id, self.token)
            connection_result = self.client.setup_session()
            
            logger.info(f"📡 Connection result: {connection_result}")
            logger.info(f"🔗 Client connected status: {self.client.is_connected}")
            
            if self.client.is_connected:
                logger.info("✅ Client connected successfully, saving session...")
                # Save or update session in database
                session, created = UserSession.objects.get_or_create(
                    user_id=self.user_id,
                    defaults={
                        'token': self.token,
                        'is_active': True,
                        'expires_at': timezone.now() + timedelta(hours=8)  # Token expires in 8 hours
                    }
                )
                
                if not created:
                    session.token = self.token
                    session.is_active = True
                    session.expires_at = timezone.now() + timedelta(hours=8)
                    session.save()
                
                logger.info(f"💾 Session {'created' if created else 'updated'} in database")
                return True
            else:
                logger.error("❌ Client connection failed")
                return False
                
        except Exception as e:
            logger.error(f"💥 Error setting up Flattrade client: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def get_or_create_stock(self, symbol, token, exchange='NSE', search_exchange=None):
        """Get or create stock in database"""
        try:
            # Skip BL (blacklisted) stocks
            if symbol.endswith('-BL'):
                logger.warning(f"⚠️ Skipping BL stock: {symbol} (blacklisted/suspended)")
                return None
            
            # Use search_exchange if provided (from multi-exchange search)
            actual_exchange = search_exchange or exchange
            
            logger.info(f"🏢 Getting/creating stock: {symbol}, token: {token}, exchange: {actual_exchange}")
            stock, created = Stock.objects.get_or_create(
                symbol=symbol,
                defaults={
                    'token': token,
                    'exchange': actual_exchange,
                    'company_name': self._generate_company_name(symbol, actual_exchange)
                }
            )
            logger.info(f"📝 Stock {'created' if created else 'found'}: {stock}")
            return stock
        except Exception as e:
            logger.error(f"💥 Error creating stock {symbol}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _generate_company_name(self, symbol, exchange):
        """Generate company name based on symbol and exchange"""
        if exchange in ['NSE_INDEX', 'INDICES']:
            # For indices, keep the name cleaner
            return symbol.replace('-', ' ').replace('_', ' ').title()
        else:
            # For stocks, remove -EQ suffix
            return symbol.replace('-EQ', '').replace('-', ' ').title()
    
    def get_live_quote(self, symbol):
        """Get live quote for a stock"""
        logger.info(f"📈 Getting live quote for: {symbol}")
        
        if not self.client or not self.client.is_connected:
            logger.warning("⚠️ Client not connected, attempting to reconnect...")
            if not self.setup_client():
                logger.error("❌ Failed to setup client for live quote")
                return None
        
        try:
            logger.info(f"🔄 Calling API for live quotes: {symbol}")
            quote_data = self.client.get_live_quotes(symbol)
            
            logger.info(f"📊 Raw quote response: {json.dumps(quote_data, indent=2, default=str)}")
            
            if quote_data and quote_data.get('stat') == 'Ok':
                logger.info("✅ Quote data received successfully")
                # Find or create stock
                token = quote_data.get('token', '')
                logger.info(f"🏷️ Stock token from quote: {token}")
                
                stock = self.get_or_create_stock(symbol, token)
                
                if stock:
                    logger.info(f"📝 Creating live quote record for stock: {stock}")
                    # Create live quote record
                    live_quote = LiveQuote.objects.create(
                        stock=stock,
                        ltp=Decimal(str(quote_data.get('lp', 0))),
                        open_price=Decimal(str(quote_data.get('o', 0))),
                        high_price=Decimal(str(quote_data.get('h', 0))),
                        low_price=Decimal(str(quote_data.get('l', 0))),
                        volume=int(quote_data.get('v', 0)),
                        change=Decimal(str(quote_data.get('c', 0))),
                        change_percent=Decimal(str(quote_data.get('prctyp', 0)))
                    )
                    
                    logger.info(f"✅ Live quote created: {live_quote}")
                    return live_quote
                else:
                    logger.error("❌ Failed to create/get stock")
            else:
                logger.error(f"❌ Quote API response error: {quote_data}")
                    
        except Exception as e:
            logger.error(f"💥 Error getting live quote for {symbol}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def get_ohlc_data(self, symbol, interval=5, days=1):
        """Get OHLC data for a stock"""
        logger.info(f"📊 Getting OHLC data for: {symbol}, interval: {interval}")
        
        if not self.client or not self.client.is_connected:
            logger.warning("⚠️ Client not connected, attempting to reconnect...")
            if not self.setup_client():
                logger.error("❌ Failed to setup client for OHLC data")
                return None
        
        try:
            # Get the stock from database to get its token
            try:
                stock = Stock.objects.get(symbol=symbol)
                token = stock.token
                logger.info(f"🔄 Found stock {symbol} with token {token}")
            except Stock.DoesNotExist:
                logger.error(f"❌ Stock {symbol} not found in database")
                return None
            
            # Use the generic OHLC method for any stock
            logger.info(f"🔄 Calling get_ohlc_data() for {symbol} (token: {token})...")
            ohlc_response = self.client.get_ohlc_data(
                token=token,
                exchange='NSE',
                interval=interval,
                days=days
            )
            
            logger.info(f"📈 Raw OHLC response: {json.dumps(ohlc_response, indent=2, default=str)}")
            
            if ohlc_response and ohlc_response.get('stat') == 'Ok':
                data = ohlc_response.get('data', [])
                logger.info(f"📋 Found {len(data)} OHLC data points")
                
                # Use the stock we already found
                logger.info(f"🏢 Stock object: {stock}")
                
                if stock:
                    ohlc_records = []
                    successful_records = 0
                    skipped_records = 0
                    
                    for i, item in enumerate(data):
                        logger.debug(f"📦 Processing OHLC item {i+1}: {item}")
                        
                        # Parse timestamp
                        timestamp_str = item.get('time', '')
                        try:
                            timestamp = datetime.strptime(timestamp_str, '%d-%m-%Y %H:%M:%S')
                            timestamp = timezone.make_aware(timestamp)
                            logger.debug(f"⏰ Parsed timestamp: {timestamp}")
                        except ValueError as ve:
                            logger.warning(f"⚠️ Skipping invalid timestamp '{timestamp_str}': {ve}")
                            skipped_records += 1
                            continue
                        
                        # Create OHLC record
                        ohlc_record, created = OHLCData.objects.get_or_create(
                            stock=stock,
                            timestamp=timestamp,
                            interval=interval,
                            defaults={
                                'open_price': Decimal(str(item.get('into', 0))),
                                'high_price': Decimal(str(item.get('inth', 0))),
                                'low_price': Decimal(str(item.get('intl', 0))),
                                'close_price': Decimal(str(item.get('intc', 0))),
                                'volume': int(item.get('v', 0))
                            }
                        )
                        
                        if created:
                            ohlc_records.append(ohlc_record)
                            successful_records += 1
                            logger.debug(f"✅ Created OHLC record: {ohlc_record}")
                        else:
                            logger.debug(f"📝 OHLC record already exists: {ohlc_record}")
                    
                    logger.info(f"📊 OHLC Summary: {successful_records} new records, {skipped_records} skipped, {len(ohlc_records)} total new")
                    return ohlc_records
                else:
                    logger.error("❌ Failed to create/get stock for OHLC data")
            else:
                logger.error(f"❌ OHLC API response error: {ohlc_response}")
                    
        except Exception as e:
            logger.error(f"💥 Error getting OHLC data for {symbol}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def search_stocks(self, search_text):
        """Search for stocks and indices across multiple exchanges"""
        if not self.client or not self.client.is_connected:
            if not self.setup_client():
                return []
        
        try:
            search_result = self.client.search_stock(search_text)
            
            if search_result and search_result.get('stat') == 'Ok':
                stocks = []
                for item in search_result.get('values', []):
                    symbol = item.get('tsym', '')
                    token = item.get('token', '')
                    search_exchange = item.get('search_exchange', 'NSE')
                    
                    if symbol and token:
                        stock = self.get_or_create_stock(
                            symbol=symbol, 
                            token=token, 
                            search_exchange=search_exchange
                        )
                        if stock:
                            stocks.append(stock)
                
                logger.info(f"🔍 Search for '{search_text}' returned {len(stocks)} stocks")
                return stocks
                
        except Exception as e:
            logger.error(f"💥 Error searching stocks: {e}")
            return []
    
    def get_popular_stocks(self):
        """Get list of popular stocks"""
        popular_symbols = [
            ('RELIANCE-EQ', '2885'),
            ('TCS-EQ', '11536'),
            ('HDFCBANK-EQ', '1333'),
            ('ICICIBANK-EQ', '4963'),
            ('HINDUNILVR-EQ', '356'),
            ('INFY-EQ', '1594'),
            ('ITC-EQ', '424'),
            ('KOTAKBANK-EQ', '1922'),
            ('LT-EQ', '2939'),
            ('AXISBANK-EQ', '5900')
        ]
        
        stocks = []
        for symbol, token in popular_symbols:
            stock = self.get_or_create_stock(symbol, token)
            if stock:
                stocks.append(stock)
        
        return stocks
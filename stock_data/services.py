"""
Django services for Flattrade API integration
"""

import sys
import os
import json
import logging
import asyncio
import concurrent.futures
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache

# Add the project root to Python path to import flattrade_client
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flattrade_client import FlattradeClient
from credentials import USER_ID, TOKEN
from .models import Stock, OHLCData, UserSession, LiveQuote, Index, IndexOHLCData, IndexQuote

# Singleton service instance
_service_instance = None

# Set up logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Hardcoded mapping for major indices (verified NSE tokens 2025)
MAJOR_INDICES = {
    'NIFTY_BANK': {
        'token': '26009',  # ✅ Verified Bank Nifty token
        'name': 'Nifty Bank',
        'symbol': 'NIFTY_BANK',
        'exchange': 'NSE'
    },
    'NIFTY': {
        'token': '26000',  # ✅ Verified Nifty 50 token
        'name': 'Nifty 50',
        'symbol': 'NIFTY',
        'exchange': 'NSE'
    },
    'NIFTY_NEXT_50': {
        'token': '26013',  # ✅ Verified Nifty Next 50 token
        'name': 'Nifty Next 50',
        'symbol': 'NIFTY_NEXT_50',
        'exchange': 'NSE'
    },
    'NIFTY_IT': {
        'token': '26008',  # ✅ Corrected from 26005 to 26008
        'name': 'Nifty IT',
        'symbol': 'NIFTY_IT',
        'exchange': 'NSE'
    },
    'NIFTY_AUTO': {
        'token': '26029',  # ✅ Corrected from 26002 to 26029
        'name': 'Nifty Auto',
        'symbol': 'NIFTY_AUTO',
        'exchange': 'NSE'
    },
    'NIFTY_FMCG': {
        'token': '26021',  # ✅ Corrected from 26003 to 26021
        'name': 'Nifty FMCG',
        'symbol': 'NIFTY_FMCG',
        'exchange': 'NSE'
    },
    'NIFTY_PHARMA': {
        'token': '26023',  # ✅ Corrected from 26008 to 26023
        'name': 'Nifty Pharma',
        'symbol': 'NIFTY_PHARMA',
        'exchange': 'NSE'
    },
    'NIFTY_REALTY': {
        'token': '26018',  # ✅ Corrected from 26010 to 26018
        'name': 'Nifty Realty',
        'symbol': 'NIFTY_REALTY',
        'exchange': 'NSE'
    },
    'NIFTY_500': {
        'token': '26004',  # ✅ Added (was incorrectly labeled as Financial Services)
        'name': 'Nifty 500',
        'symbol': 'NIFTY_500',
        'exchange': 'NSE'
    },
    'NIFTY_100': {
        'token': '26012',  # ✅ Added Nifty 100
        'name': 'Nifty 100',
        'symbol': 'NIFTY_100',
        'exchange': 'NSE'
    }
}

class FlattradeService:
    """Service class for handling Flattrade API operations"""
    
    def __init__(self):
        self.client = None
        self.user_id = USER_ID
        self.token = TOKEN
        self.setup_client()
        # Skip token validation on init for performance
    
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
            # Get stock from database first to determine exchange
            try:
                stock = Stock.objects.get(symbol=symbol)
                exchange = stock.exchange
                logger.info(f"🔄 Found stock {symbol} with exchange {exchange}")
            except Stock.DoesNotExist:
                # If stock doesn't exist, default to NSE for now
                exchange = 'NSE'
                logger.info(f"🔄 Stock {symbol} not found in database, defaulting to NSE")
            
            logger.info(f"🔄 Calling API for live quotes: {symbol} on {exchange}")
            quote_data = self.client.get_live_quotes(symbol, exchange)
            
            logger.info(f"📊 Raw quote response: {json.dumps(quote_data, indent=2, default=str)}")
            
            if quote_data and quote_data.get('stat') == 'Ok':
                logger.info("✅ Quote data received successfully")
                # Find or create stock
                token = quote_data.get('token', '')
                logger.info(f"🏷️ Stock token from quote: {token}")
                
                stock = self.get_or_create_stock(symbol, token, exchange)
                
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
            logger.info(f"🔄 Calling get_ohlc_data() for {symbol} (token: {token}, exchange: {stock.exchange})...")
            ohlc_response = self.client.get_ohlc_data(
                token=token,
                exchange=stock.exchange,
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
        """Search for stocks and indices with hardcoded mapping priority"""
        if not self.client or not self.client.is_connected:
            if not self.setup_client():
                return []
        
        try:
            results = []
            
            # First, check if search matches any hardcoded major indices
            search_lower = search_text.lower()
            for symbol, info in MAJOR_INDICES.items():
                if (search_lower in symbol.lower() or 
                    search_lower in info['name'].lower()):
                    
                    index = self.get_or_create_index(
                        symbol=symbol,
                        token=info['token'],
                        name=info['name']
                    )
                    if index:
                        results.append(index)
                        logger.info(f"🎯 Found hardcoded index: {symbol}")
            
            # Then do API search for additional results
            search_result = self.client.search_stock(search_text)
            
            if search_result and search_result.get('stat') == 'Ok':
                for item in search_result.get('values', []):
                    symbol = item.get('tsym', '')
                    token = item.get('token', '')
                    search_exchange = item.get('search_exchange', 'NSE')
                    instname = item.get('instname', '')
                    
                    if symbol and token:
                        # Skip if we already have this from hardcoded mapping
                        if any(hasattr(r, 'token') and r.token == token for r in results):
                            continue
                            
                        if instname == 'UNDIND' or 'NIFTY' in symbol.upper():
                            # Handle as index
                            index = self.get_or_create_index(
                                symbol=symbol,
                                token=token,
                                name=item.get('cname', symbol)
                            )
                            if index:
                                results.append(index)
                        else:
                            # Handle as stock
                            stock = self.get_or_create_stock(
                                symbol=symbol, 
                                token=token, 
                                search_exchange=search_exchange
                            )
                            if stock:
                                results.append(stock)
                
                logger.info(f"🔍 Search for '{search_text}' returned {len(results)} results")
                return results
                
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
    
    def get_or_create_index(self, symbol, token, name=None, index_type='EQUITY'):
        """Get or create index in database with hardcoded mapping priority"""
        try:
            logger.info(f"🏢 Getting/creating index: {symbol}, token: {token}")
            
            # Check if this is a major index with hardcoded mapping
            if symbol in MAJOR_INDICES:
                major_index_info = MAJOR_INDICES[symbol]
                # Use hardcoded token and name
                token = major_index_info['token']
                name = major_index_info['name']
                logger.info(f"📋 Using hardcoded mapping for {symbol}: token={token}, name={name}")
            
            index, created = Index.objects.get_or_create(
                symbol=symbol,
                token=token,
                defaults={
                    'name': name or self._generate_index_name(symbol),
                    'exchange': 'NSE',
                    'index_type': index_type,
                    'is_active': True
                }
            )
            logger.info(f"📝 Index {'created' if created else 'found'}: {index}")
            return index
        except Exception as e:
            logger.error(f"💥 Error creating index {symbol}: {e}")
            return None
    
    def _generate_index_name(self, symbol):
        """Generate readable index name from symbol"""
        name_mapping = {
            'NIFTY': 'Nifty 50',
            'NIFTY_BANK': 'Nifty Bank',
            'NIFTY_NEXT_50': 'Nifty Next 50',
            'NIFTY_100': 'Nifty 100',
            'NIFTY_IT': 'Nifty IT',
            'NIFTY_AUTO': 'Nifty Auto',
            'NIFTY_FMCG': 'Nifty FMCG',
            'NIFTY_PHARMA': 'Nifty Pharma',
        }
        return name_mapping.get(symbol, symbol.replace('_', ' ').title())
    
    def get_index_by_symbol(self, symbol):
        """Get index by symbol, using hardcoded mapping if available"""
        try:
            if symbol in MAJOR_INDICES:
                # Use hardcoded mapping
                major_index_info = MAJOR_INDICES[symbol]
                index, created = Index.objects.get_or_create(
                    symbol=symbol,
                    token=major_index_info['token'],
                    defaults={
                        'name': major_index_info['name'],
                        'exchange': major_index_info['exchange'],
                        'index_type': 'EQUITY',
                        'is_active': True
                    }
                )
                return index
            else:
                # Fall back to database lookup
                return Index.objects.get(symbol=symbol)
        except Index.DoesNotExist:
            logger.error(f"Index {symbol} not found")
            return None
        except Index.MultipleObjectsReturned:
            logger.error(f"Multiple indices found for {symbol}")
            # Return the first one as fallback
            return Index.objects.filter(symbol=symbol).first()
    
    def validate_major_indices_tokens(self):
        """Validate that major indices tokens work with the API"""
        if not self.client or not self.client.is_connected:
            logger.warning("⚠️ Cannot validate tokens - client not connected")
            return
        
        logger.info("🔍 Validating major indices tokens...")
        validation_results = {}
        
        for symbol, info in MAJOR_INDICES.items():
            try:
                token = info['token']
                logger.debug(f"🔍 Testing token {token} for {symbol}...")
                
                # Test token by trying to get quotes
                quote_response = self.client.api.get_quotes(exchange=info['exchange'], token=token)
                
                if quote_response and quote_response.get('stat') == 'Ok':
                    validation_results[symbol] = {
                        'status': 'valid',
                        'token': token,
                        'name': quote_response.get('tsym', 'Unknown')
                    }
                    logger.info(f"✅ {symbol} token {token} is valid - maps to {quote_response.get('tsym')}")
                else:
                    validation_results[symbol] = {
                        'status': 'invalid',
                        'token': token,
                        'error': quote_response
                    }
                    logger.error(f"❌ {symbol} token {token} is invalid: {quote_response}")
                    
            except Exception as e:
                validation_results[symbol] = {
                    'status': 'error',
                    'token': token,
                    'error': str(e)
                }
                logger.error(f"💥 Error validating {symbol} token {token}: {e}")
        
        # Log summary
        valid_count = sum(1 for r in validation_results.values() if r['status'] == 'valid')
        total_count = len(validation_results)
        logger.info(f"📊 Token validation complete: {valid_count}/{total_count} tokens are valid")
        
        return validation_results
    
    def get_index_quote(self, symbol):
        """Get live quote for an index using hardcoded mapping first"""
        logger.info(f"📊 Getting index quote for: {symbol}")
        
        if not self.client or not self.client.is_connected:
            logger.warning("⚠️ Client not connected, attempting to reconnect...")
            if not self.setup_client():
                logger.error("❌ Failed to setup client for index quote")
                return None
        
        try:
            # Check cache first (sanitize symbol for cache key)
            cache_key = f"index_quote_{symbol.replace(' ', '_')}"
            cached_quote = cache.get(cache_key)
            if cached_quote:
                logger.info(f"📋 Using cached quote for {symbol}")
                return cached_quote
            
            # Use hardcoded mapping if available
            if symbol in MAJOR_INDICES:
                major_index_info = MAJOR_INDICES[symbol]
                token = major_index_info['token']
                logger.info(f"🎯 Using hardcoded token {token} for {symbol}")
                
                # Get quotes directly by token (more reliable)
                quote_data = self.client.api.get_quotes(exchange=major_index_info['exchange'], token=token)
                logger.info(f"📊 Direct token call response: {json.dumps(quote_data, indent=2, default=str)}")
            else:
                # Fall back to search-based approach
                logger.info(f"🔄 Using search-based approach for {symbol}")
                quote_data = self.client.get_live_quotes(symbol)
            
            logger.info(f"📊 Raw index quote response: {json.dumps(quote_data, indent=2, default=str)}")
            
            if quote_data and quote_data.get('stat') == 'Ok':
                logger.info("✅ Index quote data received successfully")
                api_token = quote_data.get('token', '')
                
                # For major indices, use hardcoded token; otherwise use API token
                if symbol in MAJOR_INDICES:
                    final_token = MAJOR_INDICES[symbol]['token']
                    final_name = MAJOR_INDICES[symbol]['name']
                    logger.info(f"📋 Using hardcoded token {final_token} and name '{final_name}' for {symbol}")
                else:
                    final_token = api_token
                    final_name = None
                    logger.info(f"🔍 Using API token {final_token} for {symbol}")
                
                # Get or create index
                index = self.get_or_create_index(symbol, final_token, final_name)
                
                if index:
                    # Create index quote record (no volume)
                    index_quote = IndexQuote.objects.create(
                        index=index,
                        ltp=Decimal(str(quote_data.get('lp', 0))),
                        open_price=Decimal(str(quote_data.get('o', 0))),
                        high_price=Decimal(str(quote_data.get('h', 0))),
                        low_price=Decimal(str(quote_data.get('l', 0))),
                        change=Decimal(str(quote_data.get('c', 0))),
                        change_percent=Decimal(str(quote_data.get('prctyp', 0)))
                    )
                    
                    # Cache for 5 minutes
                    cache.set(cache_key, index_quote, 300)
                    
                    logger.info(f"✅ Index quote created: {index_quote}")
                    return index_quote
                else:
                    logger.error("❌ Failed to create/get index")
            else:
                logger.error(f"❌ Index quote API response error: {quote_data}")
                    
        except Exception as e:
            logger.error(f"💥 Error getting index quote for {symbol}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def get_index_ohlc_data(self, symbol, interval=5, days=1):
        """Get OHLC data for an index using hardcoded mapping first"""
        logger.info(f"📊 Getting index OHLC data for: {symbol}, interval: {interval}")
        
        if not self.client or not self.client.is_connected:
            logger.warning("⚠️ Client not connected, attempting to reconnect...")
            if not self.setup_client():
                logger.error("❌ Failed to setup client for index OHLC data")
                return None
        
        try:
            # Use hardcoded mapping if available
            if symbol in MAJOR_INDICES:
                token = MAJOR_INDICES[symbol]['token']
                logger.info(f"🎯 Using hardcoded token {token} for {symbol}")
                
                # Get or create index using hardcoded info
                index = self.get_or_create_index(
                    symbol, 
                    token, 
                    MAJOR_INDICES[symbol]['name']
                )
            else:
                # Fall back to database lookup
                try:
                    index = Index.objects.get(symbol=symbol)
                    token = index.token
                    logger.info(f"🔄 Found index {symbol} with token {token} from database")
                except Index.DoesNotExist:
                    logger.error(f"❌ Index {symbol} not found in database")
                    return None
                except Index.MultipleObjectsReturned:
                    logger.error(f"❌ Multiple indices found for {symbol} - database needs cleanup")
                    return None
            
            if not index:
                logger.error(f"❌ Could not get/create index for {symbol}")
                return None
                
            logger.info(f"🔄 Calling get_ohlc_data() for index {symbol} (token: {token}, exchange: {index.exchange})...")
            ohlc_response = self.client.get_ohlc_data(
                token=token,
                exchange=index.exchange,
                interval=interval,
                days=days
            )
            
            if ohlc_response and ohlc_response.get('stat') == 'Ok':
                data = ohlc_response.get('data', [])
                logger.info(f"📋 Found {len(data)} index OHLC data points")
                
                ohlc_records = []
                successful_records = 0
                skipped_records = 0
                
                for i, item in enumerate(data):
                    logger.debug(f"📦 Processing index OHLC item {i+1}: {item}")
                    
                    # Parse timestamp
                    timestamp_str = item.get('time', '')
                    try:
                        timestamp = datetime.strptime(timestamp_str, '%d-%m-%Y %H:%M:%S')
                        timestamp = timezone.make_aware(timestamp)
                    except ValueError as ve:
                        logger.warning(f"⚠️ Skipping invalid timestamp '{timestamp_str}': {ve}")
                        skipped_records += 1
                        continue
                    
                    # Create index OHLC record (no volume)
                    ohlc_record, created = IndexOHLCData.objects.get_or_create(
                        index=index,
                        timestamp=timestamp,
                        interval=interval,
                        defaults={
                            'open_price': Decimal(str(item.get('into', 0))),
                            'high_price': Decimal(str(item.get('inth', 0))),
                            'low_price': Decimal(str(item.get('intl', 0))),
                            'close_price': Decimal(str(item.get('intc', 0)))
                        }
                    )
                    
                    if created:
                        ohlc_records.append(ohlc_record)
                        successful_records += 1
                        logger.debug(f"✅ Created index OHLC record: {ohlc_record}")
                    else:
                        logger.debug(f"📝 Index OHLC record already exists: {ohlc_record}")
                
                logger.info(f"📊 Index OHLC Summary: {successful_records} new records, {skipped_records} skipped")
                return ohlc_records
            else:
                logger.error(f"❌ Index OHLC API response error: {ohlc_response}")
                    
        except Exception as e:
            logger.error(f"💥 Error getting index OHLC data for {symbol}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def search_with_parallel_exchanges(self, search_text):
        """Search stocks and indices across exchanges in parallel"""
        if not self.client or not self.client.is_connected:
            if not self.setup_client():
                return []
        
        try:
            exchanges = ['NSE', 'BSE', 'NFO', 'CDS', 'MCX']
            all_results = []
            
            # Use ThreadPoolExecutor for parallel API calls
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                # Submit all search tasks
                future_to_exchange = {
                    executor.submit(self._search_single_exchange, exchange, search_text): exchange 
                    for exchange in exchanges
                }
                
                # Collect results as they complete
                for future in concurrent.futures.as_completed(future_to_exchange):
                    exchange = future_to_exchange[future]
                    try:
                        results = future.result(timeout=10)  # 10 second timeout per exchange
                        if results:
                            all_results.extend(results)
                            logger.info(f"✅ {exchange}: Found {len(results)} results")
                        else:
                            logger.info(f"⚠️ {exchange}: No results")
                    except Exception as e:
                        logger.error(f"❌ {exchange} search failed: {e}")
            
            # Special handling for index discovery
            if 'nifty' in search_text.lower():
                logger.info(f"🔍 Adding index discovery for '{search_text}'")
                index_results = self._discover_indices(search_text)
                all_results.extend(index_results)
            
            # Convert results to database objects
            stocks = []
            for item in all_results:
                symbol = item.get('tsym', '')
                token = item.get('token', '')
                search_exchange = item.get('search_exchange', 'NSE')
                instname = item.get('instname', '')
                
                if symbol and token:
                    if instname == 'INDEX' or 'NIFTY' in symbol:
                        # Handle as index
                        index = self.get_or_create_index(
                            symbol=symbol,
                            token=token,
                            name=item.get('cname', symbol)
                        )
                        if index:
                            stocks.append(index)
                    else:
                        # Handle as stock
                        stock = self.get_or_create_stock(
                            symbol=symbol, 
                            token=token, 
                            search_exchange=search_exchange
                        )
                        if stock:
                            stocks.append(stock)
            
            logger.info(f"🔍 Parallel search for '{search_text}' returned {len(stocks)} items")
            return stocks
                
        except Exception as e:
            logger.error(f"💥 Error in parallel search: {e}")
            return []

def get_flattrade_service():
    """Get singleton FlattradeService instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = FlattradeService()
    return _service_instance
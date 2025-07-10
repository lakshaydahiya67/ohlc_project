import datetime
from api_helper import NorenApiPy

class FlattradeClient:
    def __init__(self, userid, token):
        """
        Initialize Flattrade client with user credentials
        
        Args:
            userid (str): Your Flattrade user ID
            token (str): Daily generated token
        """
        self.api = NorenApiPy()
        self.userid = userid
        self.token = token
        self.is_connected = False
        
    def setup_session(self):
        """
        Set up session with Flattrade API
        
        Returns:
            dict: Response from API
        """
        try:
            ret = self.api.set_session(
                userid=self.userid,
                password='',
                usertoken=self.token
            )
            
            # Check if ret is a dictionary and has the expected structure
            if isinstance(ret, dict) and ret.get('stat') == 'Ok':
                self.is_connected = True
                print(f"✅ Connected successfully as {self.userid}")
                return ret
            elif ret is True:
                # Some versions of the API return True on successful connection
                self.is_connected = True
                print(f"✅ Connected successfully as {self.userid}")
                return {"stat": "Ok", "userid": self.userid}
            else:
                self.is_connected = False
                if isinstance(ret, dict):
                    error_msg = ret.get('emsg', 'Unknown error')
                    print(f"❌ Connection failed: {error_msg}")
                else:
                    print(f"❌ Connection failed: Invalid response - {ret}")
                return ret
                
        except Exception as e:
            self.is_connected = False
            print(f"❌ Error connecting: {e}")
            return None
    
    def get_ohlc_data(self, token, exchange='NSE', interval=5, start_time=None):
        """
        Fetch OHLC data for a given stock token.
        
        Args:
            token (str): The scrip token.
            exchange (str, optional): The exchange. Defaults to 'NSE'.
            interval (int, optional): The candle interval in minutes. Defaults to 5.
            start_time (datetime.datetime, optional): The start time for the data. 
                                                     Defaults to the beginning of today.
        
        Returns:
            dict: OHLC data response
        """
        if not self.is_connected:
            print("❌ Not connected. Please run setup_session() first.")
            return None

        try:
            if start_time is None:
                # Set start time to beginning of today
                start_time = datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)

            print(f"📊 Fetching OHLC data for token {token} from {start_time}")

            ret = self.api.get_time_price_series(
                exchange=exchange,
                token=token,
                starttime=start_time.timestamp(),
                interval=interval
            )

            if ret and ret.get('stat') == 'Ok':
                print(f"✅ Retrieved {len(ret.get('data', []))} data points")
                return ret
            else:
                print(f"❌ Failed to fetch data: {ret}")
                return ret

        except Exception as e:
            print(f"❌ Error fetching OHLC data: {e}")
            return None
    
    def get_live_quotes(self, symbol='RELIANCE-EQ', exchange='NSE'):
        """
        Get live quotes for a stock
        
        Args:
            symbol (str): Trading symbol (default: RELIANCE-EQ)
            exchange (str): Exchange (default: NSE)
            
        Returns:
            dict: Live quotes data
        """
        if not self.is_connected:
            print("❌ Not connected. Please run setup_session() first.")
            return None
            
        try:
            # For quotes, we need to get the token first
            # If symbol is provided as token, use it directly
            if symbol.isdigit():
                token = symbol
            else:
                # Search for the token using the symbol
                search_result = self.api.searchscrip(exchange=exchange, searchtext=symbol.replace('-EQ', ''))
                if search_result and search_result.get('values'):
                    token = search_result['values'][0]['token']
                else:
                    print(f"❌ Could not find token for symbol: {symbol}")
                    return None
            
            quotes = self.api.get_quotes(exchange=exchange, token=token)
            
            if quotes and quotes.get('stat') == 'Ok':
                print(f"✅ Live quotes for {symbol}:")
                print(f"   LTP: ₹{quotes.get('lp', 'N/A')}")
                print(f"   Open: ₹{quotes.get('o', 'N/A')}")
                print(f"   High: ₹{quotes.get('h', 'N/A')}")
                print(f"   Low: ₹{quotes.get('l', 'N/A')}")
                return quotes
            else:
                print(f"❌ Failed to fetch quotes: {quotes}")
                return quotes
                
        except Exception as e:
            print(f"❌ Error fetching quotes: {e}")
            return None
    
    def get_major_indices_info(self):
        """
        Get information about major indices by testing known tokens
        This is discovery-based, not hardcoded user data
        
        Returns:
            list: List of major indices with their details
        """
        major_indices_tokens = [
            ('26000', 'NIFTY'),           # Main Nifty 50 
            ('99926000', 'NIFTY'),        # New Nifty 50 token
            ('26001', 'NIFTY BANK'),      # Bank Nifty
            ('99926001', 'NIFTY BANK'),   # New Bank Nifty token
        ]
        
        discovered_indices = []
        
        for token, expected_symbol in major_indices_tokens:
            try:
                print(f"🔍 Testing token {token} for {expected_symbol}...")
                # Try to get quotes to verify if token exists
                quotes = self.api.get_quotes(exchange='NSE', token=token)
                
                if quotes and quotes.get('stat') == 'Ok':
                    discovered_indices.append({
                        'token': token,
                        'tsym': expected_symbol,
                        'exch': 'NSE',
                        'instname': 'INDEX',
                        'search_exchange': 'NSE',
                        'cname': f'{expected_symbol} Index',
                        'discovered': True
                    })
                    print(f"✅ Discovered: {expected_symbol} with token {token}")
                else:
                    print(f"❌ Token {token} not valid for {expected_symbol}")
                    
            except Exception as e:
                print(f"❌ Error testing token {token}: {e}")
                continue
        
        return discovered_indices

    def search_stock(self, search_text):
        """
        Search for stocks and indices by name across multiple exchanges
        Also includes discovery of major indices if searching for 'nifty'
        
        Args:
            search_text (str): Text to search for
            
        Returns:
            dict: Combined search results from multiple exchanges
        """
        if not self.is_connected:
            print("❌ Not connected. Please run setup_session() first.")
            return None
            
        all_results = []
        exchanges_to_search = ['NSE', 'BSE', 'NFO', 'CDS', 'MCX']
        
        for exchange in exchanges_to_search:
            try:
                print(f"🔍 Searching in {exchange} for '{search_text}'...")
                ret = self.api.searchscrip(exchange=exchange, searchtext=search_text)
                
                print(f"📋 Raw response from {exchange}: {ret}")
                
                if ret and ret.get('stat') == 'Ok' and ret.get('values'):
                    results = ret.get('values', [])
                    # Add exchange info to each result for identification
                    for result in results:
                        result['search_exchange'] = exchange
                        # Debug: Print each result to see what we're getting
                        print(f"   📊 Found: {result.get('tsym', 'N/A')} | Token: {result.get('token', 'N/A')} | Type: {result.get('instname', 'N/A')}")
                    all_results.extend(results)
                    print(f"✅ Found {len(results)} results in {exchange}")
                elif ret and ret.get('stat') == 'Ok':
                    print(f"⚠️ {exchange} returned OK but no values")
                else:
                    print(f"⚠️ No results in {exchange}: {ret}")
                    
            except Exception as e:
                print(f"❌ Error searching {exchange}: {e}")
                continue
        
        # If searching for 'nifty', also try to discover major indices
        print(f"DEBUG: Checking if '{search_text}' contains 'nifty': {'nifty' in search_text.lower()}")
        if 'nifty' in search_text.lower():
            print(f"🔍 DISCOVERY STARTING: Also discovering major indices for search: '{search_text}'...")
            try:
                discovered_indices = self.get_major_indices_info()
                print(f"DEBUG: Discovery returned {len(discovered_indices) if discovered_indices else 0} indices")
                if discovered_indices:
                    all_results.extend(discovered_indices)
                    print(f"✅ Added {len(discovered_indices)} discovered indices")
                else:
                    print(f"⚠️ No indices discovered through token testing")
            except Exception as e:
                print(f"❌ Error during index discovery: {e}")
                import traceback
                print(traceback.format_exc())

        if all_results:
            print(f"✅ Total found: {len(all_results)} results across all exchanges")
            return {
                'stat': 'Ok',
                'values': all_results
            }
        else:
            print(f"❌ No results found for '{search_text}' in any exchange")
            return {
                'stat': 'Not_Ok',
                'emsg': f'No results found for {search_text}'
            }
    
    def get_reliance_ohlc_5min(self):
        """
        Fetch Reliance OHLC data with 5-minute intervals
        
        Returns:
            dict: OHLC data response
        """
        if not self.is_connected:
            print("❌ Not connected. Please run setup_session() first.")
            return None
            
        try:
            # Set start time to beginning of today
            lastBusDay = datetime.datetime.today()
            lastBusDay = lastBusDay.replace(hour=0, minute=0, second=0, microsecond=0)
            
            print(f"📊 Fetching Reliance OHLC data from {lastBusDay}")
            
            ret = self.api.get_time_price_series(
                exchange='NSE',  # Reliance is on NSE
                token='2885',  # Reliance token
                starttime=lastBusDay.timestamp(),
                interval=5  # 5-minute intervals
            )
            
            if isinstance(ret, list) and ret:
                print(f"✅ Retrieved {len(ret)} OHLC data points")
                return {"stat": "Ok", "data": ret}
            elif isinstance(ret, dict) and ret.get('stat') == 'Ok':
                print(f"✅ Retrieved {len(ret.get('data', []))} data points")
                return ret
            else:
                print(f"❌ Failed to fetch data: {ret}")
                return ret
                
        except Exception as e:
            print(f"❌ Error fetching OHLC data: {e}")
            return None
    
    def get_ohlc_data(self, token, exchange='NSE', interval=5, days=1):
        """
        Fetch OHLC data for any stock using its token
        
        Args:
            token (str): Stock token (e.g., '2885' for Reliance, '5900' for AXISBANK)
            exchange (str): Exchange name (default: 'NSE')
            interval (int): Time interval in minutes (1, 3, 5, 15, 30, 60)
            days (int): Number of days of data to fetch (default: 1)
        
        Returns:
            dict: OHLC data response
        """
        if not self.is_connected:
            print("❌ Not connected. Please run setup_session() first.")
            return None
            
        try:
            # Set start time based on days parameter
            start_date = datetime.datetime.today() - datetime.timedelta(days=days-1)
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            print(f"📊 Fetching OHLC data for token {token} from {start_date}, interval: {interval}min")
            
            ret = self.api.get_time_price_series(
                exchange=exchange,
                token=token,
                starttime=start_date.timestamp(),
                interval=interval
            )
            
            if isinstance(ret, list) and ret:
                print(f"✅ Retrieved {len(ret)} OHLC data points for token {token}")
                return {"stat": "Ok", "data": ret}
            elif isinstance(ret, dict) and ret.get('stat') == 'Ok':
                print(f"✅ Retrieved {len(ret.get('data', []))} data points for token {token}")
                return ret
            else:
                print(f"❌ Failed to fetch data for token {token}: {ret}")
                return ret
                
        except Exception as e:
            print(f"❌ Error fetching OHLC data for token {token}: {e}")
            return None

# Example usage (you'll need to replace with your actual credentials)
if __name__ == "__main__":
    # Replace these with your actual credentials
    USER_ID = "your_user_id"
    TOKEN = "your_daily_token"
    
    print("🚀 Starting Flattrade Client Demo")
    print("="*50)
    
    # Create client instance
    client = FlattradeClient(USER_ID, TOKEN)
    
    # Setup session
    print("\n1. Setting up session...")
    session_result = client.setup_session()
    
    if client.is_connected:
        # Get live quotes
        print("\n2. Getting live quotes...")
        quotes = client.get_live_quotes()
        
        # Search for stocks
        print("\n3. Searching for stocks...")
        search_result = client.search_stock("RELIANCE")
        
        # Get OHLC data
        print("\n4. Getting OHLC data...")
        ohlc_data = client.get_ohlc_data(token='2885') # Reliance token
        
        if ohlc_data and ohlc_data.get('data'):
            print(f"\nSample OHLC data (first 3 entries):")
            for i, entry in enumerate(ohlc_data['data'][:3]):
                print(f"  {i+1}. Time: {entry.get('time')}, Open: {entry.get('into')}, High: {entry.get('inth')}, Low: {entry.get('intl')}, Close: {entry.get('intc')}")
    
    print("\n✅ Demo completed!")
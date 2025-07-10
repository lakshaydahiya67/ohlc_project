# OHLC Django Project - Flattrade API Integration

## Project Overview
A Django-based web application that integrates with Flattrade's free API to fetch, store, and display real-time stock market OHLC (Open, High, Low, Close) data. The project includes user authentication, live quotes, multi-exchange stock search, and comprehensive data visualization.

## Key Resources
- **GitHub Repository**: https://github.com/flattrade/pythonAPI
- **Official Documentation**: https://pi.flattrade.in/docs
- **Wall Dashboard**: https://wall.flattrade.in (for API key generation)

## Authentication Setup (Already Configured)
✅ **User credentials and daily token are already set up in `credentials.py` and `daily_token.txt`**
- API authentication is handled automatically through the `FlattradeService` class
- Session management is implemented in Django models (`UserSession`)
- No manual token generation required for development

## Implemented Features

### ✅ Core Components
1. **Django Models** (`stock_data/models.py`):
   - `Stock`: Stores stock information (symbol, token, exchange, company name)
   - `OHLCData`: Historical OHLC data with timestamps and intervals
   - `UserSession`: API session management and token expiry tracking
   - `LiveQuote`: Real-time stock quotes with price changes

2. **Flattrade Service** (`stock_data/services.py`):
   - `FlattradeService`: Main service class for API operations
   - Automatic session setup and reconnection
   - Comprehensive error handling and logging
   - Database integration for caching stock data

3. **Flattrade Client** (`flattrade_client.py`):
   - `FlattradeClient`: Low-level API wrapper
   - Session management with connection status tracking
   - Multi-exchange stock search with index discovery
   - Live quotes and OHLC data fetching

4. **Django Views** (`stock_data/views.py`):
   - Dashboard with stock statistics and recent data
   - Stock detail pages with OHLC charts
   - Search functionality across multiple exchanges
   - AJAX endpoints for live data updates

### ✅ API Endpoints Implementation

#### 1. OHLC Data Fetching
```python
# Get OHLC data for any stock
ohlc_data = flattrade_service.get_ohlc_data(symbol='RELIANCE-EQ', interval=5, days=1)

# Implementation uses get_time_price_series() internally
ret = api.get_time_price_series(
    exchange='NSE',
    token=stock.token,
    starttime=start_date.timestamp(),
    interval=interval  # 1, 3, 5, 15, 30, 60 minutes
)
```

#### 2. Live Quotes
```python
# Get real-time market quotes
live_quote = flattrade_service.get_live_quote('RELIANCE-EQ')

# Returns LiveQuote model with LTP, OHLC, volume, changes
```

#### 3. Multi-Exchange Stock Search
```python
# Search across NSE, BSE, NFO, CDS, MCX
search_results = flattrade_service.search_stocks('RELIANCE')

# Includes automatic Nifty index discovery for 'nifty' searches
```

## Comprehensive Flattrade API Reference

### 🔥 Complete API Methods Available

#### Order Management (Production Ready)
```python
# Place order
ret = api.place_order(
    buy_or_sell='B',           # 'B' for Buy, 'S' for Sell
    product_type='C',          # 'C' for Cash, 'M' for Margin, 'H' for Cover Order
    exchange='NSE',
    tradingsymbol='RELIANCE-EQ',
    quantity=1,
    discloseqty=0,            # Disclosed quantity (0 means not disclosed)
    price_type='LMT',         # 'LMT' for Limit, 'MKT' for Market, 'SL-LMT' for Stop Loss Limit
    price=2500.00,            # Price (for limit orders)
    trigger_price=2450.00,    # Trigger price (for stop loss orders)
    retention='DAY',          # 'DAY' or 'IOC' (Immediate or Cancel)
    remarks='trade_001'       # Custom remarks
)

# Modify existing order
ret = api.modify_order(
    orderno='order_number',
    exchange='NSE',
    tradingsymbol='RELIANCE-EQ',
    newquantity=2,
    newprice_type='LMT',
    newprice=2550.00
)

# Cancel order
ret = api.cancel_order(orderno='order_number')

# Exit cover/bracket order
ret = api.exit_order(orderno='order_number', product_type='H')
```

#### Portfolio & Position Management
```python
# Get order book (all orders)
orders = api.get_order_book()

# Get trade book (executed trades)
trades = api.get_trade_book()

# Get holdings (delivery positions)
holdings = api.get_holdings()

# Get positions (intraday & carry forward)
positions = api.get_positions()

# Get account limits (available margin)
limits = api.get_limits()
```

#### Market Data & Search
```python
# Search instruments across exchanges
search_results = api.searchscrip(exchange='NSE', searchtext='RELIANCE')

# Get security/instrument information
security_info = api.get_security_info(exchange='NSE', token='2885')

# Get live quotes
quotes = api.get_quotes(exchange='NSE', token='2885')

# Get historical daily data
daily_data = api.get_daily_price_series(
    exchange='NSE',
    tradingsymbol='RELIANCE-EQ',
    startdate=0  # 0 for all available data
)

# Get intraday time series
intraday_data = api.get_time_price_series(
    exchange='NSE',
    token='2885',
    starttime=timestamp,
    interval=5  # 1, 3, 5, 15, 30, 60 minutes
)

# Get option chain (for derivatives)
option_chain = api.get_option_chain(
    exchange='NFO',
    tradingsymbol='NIFTY',
    strikeprice='19000',
    count='10'
)
```

#### WebSocket Streaming (Real-time Data)
```python
# Start WebSocket connection
api.start_websocket(
    order_update_callback=order_callback,
    subscribe_callback=feed_callback,
    socket_error_callback=error_callback
)

# Subscribe to live feeds
api.subscribe(['NSE|2885'])  # Reliance live data
api.subscribe(['NSE|26000']) # Nifty 50 index

# Unsubscribe from feeds
api.unsubscribe(['NSE|2885'])
```

### 📊 Popular Stock Tokens (Pre-configured)
Our system includes these popular stocks:

| Stock | Symbol | Token | Exchange |
|-------|--------|-------|----------|
| Reliance | RELIANCE-EQ | 2885 | NSE |
| TCS | TCS-EQ | 11536 | NSE |
| HDFC Bank | HDFCBANK-EQ | 1333 | NSE |
| ICICI Bank | ICICIBANK-EQ | 4963 | NSE |
| Hindustan Unilever | HINDUNILVR-EQ | 356 | NSE |
| Infosys | INFY-EQ | 1594 | NSE |
| ITC | ITC-EQ | 424 | NSE |
| Kotak Bank | KOTAKBANK-EQ | 1922 | NSE |
| L&T | LT-EQ | 2939 | NSE |
| Axis Bank | AXISBANK-EQ | 5900 | NSE |

### 🏢 Supported Exchanges
- **NSE**: National Stock Exchange (Equities)
- **BSE**: Bombay Stock Exchange (Equities)
- **NFO**: NSE Futures & Options
- **CDS**: Currency Derivatives Segment
- **MCX**: Multi Commodity Exchange

### ⚙️ Configuration & Settings

#### Interval Options for OHLC Data
- `1` = 1 minute
- `3` = 3 minutes  
- `5` = 5 minutes (default in our app)
- `15` = 15 minutes
- `30` = 30 minutes
- `60` = 1 hour

#### Product Types for Trading
- `'C'` = Cash/Delivery (normal equity trading)
- `'M'` = Margin/Intraday 
- `'H'` = Cover Order (with stop loss)
- `'B'` = Bracket Order (with target and stop loss)

#### Order Types
- `'LMT'` = Limit Order (specify price)
- `'MKT'` = Market Order (execute at market price)
- `'SL-LMT'` = Stop Loss Limit
- `'SL-MKT'` = Stop Loss Market

### 🔒 Security & Best Practices
- ✅ **Session management**: Automatic token validation and reconnection
- ✅ **Error handling**: Comprehensive logging and exception management
- ✅ **Rate limiting**: Built-in API call optimization
- ✅ **Data validation**: Input sanitization and response verification
- ✅ **Database caching**: Reduces API calls and improves performance

## 🚀 Project Structure & Implementation Status

### ✅ Completed Components

#### 1. **Django Models** (`stock_data/models.py`)
- **Stock**: Company information with tokens and exchange data
- **OHLCData**: Time-series price data with intervals
- **UserSession**: API session management with expiry tracking  
- **LiveQuote**: Real-time market quotes with change tracking

#### 2. **Flattrade Integration** (`flattrade_client.py`)
- **FlattradeClient**: Core API wrapper with session management
- **Multi-exchange search**: NSE, BSE, NFO, CDS, MCX support
- **Index discovery**: Automatic Nifty index detection
- **Error handling**: Comprehensive logging and reconnection logic

#### 3. **Django Service Layer** (`stock_data/services.py`)
- **FlattradeService**: Business logic and database integration
- **Automatic reconnection**: Session management with token validation
- **Data persistence**: OHLC and quote data caching in database
- **Popular stocks**: Pre-configured list of major Indian stocks

#### 4. **Web Interface** (`stock_data/views.py`)
- **Dashboard**: Stock statistics and recent data overview
- **Stock detail pages**: Individual stock OHLC charts
- **Search functionality**: Multi-exchange stock search
- **AJAX endpoints**: Live data updates without page refresh

#### 5. **Templates & Frontend**
- **Base template**: Bootstrap-based responsive design
- **Dashboard**: Summary cards and recent data tables  
- **Stock detail**: OHLC data tables with pagination
- **Search page**: Real-time search with API integration

### 🎯 Usage Examples

#### Getting Live Stock Data
```python
# Initialize service (automatic authentication)
flattrade_service = FlattradeService()

# Get live quote for any stock
live_quote = flattrade_service.get_live_quote('RELIANCE-EQ')
print(f"LTP: ₹{live_quote.ltp}")

# Fetch OHLC data with custom parameters  
ohlc_data = flattrade_service.get_ohlc_data(
    symbol='TCS-EQ', 
    interval=5,      # 5-minute candles
    days=3          # Last 3 days
)
```

#### Multi-Exchange Search
```python
# Search across all exchanges
results = flattrade_service.search_stocks('NIFTY')
# Returns: NSE stocks + discovered Nifty indices

# Database integration automatic
for stock in results:
    print(f"{stock.symbol} ({stock.token}) - {stock.exchange}")
```

### 🛠️ Management Commands

#### Fetch Sample Data
```bash
python manage.py fetch_sample_data
```
- Fetches popular stocks data
- Updates OHLC records
- Refreshes live quotes

### 🔧 Development Tools

#### Logging & Debugging
- **Comprehensive logging**: All API calls logged with timestamps
- **Error tracking**: Exception handling with stack traces
- **Session monitoring**: Connection status and token expiry alerts

#### Database Management
- **Automatic migrations**: Model changes handled by Django
- **Data integrity**: Unique constraints on stock symbols and timestamps
- **Performance optimization**: Database indexes on frequently queried fields

### 📈 API Rate Limits & Best Practices
- **Session reuse**: Single session for multiple API calls
- **Database caching**: Reduces redundant API requests
- **Error recovery**: Automatic reconnection on session timeout
- **Data validation**: Input sanitization and response verification

### 🌟 Advanced Features Ready for Implementation

#### WebSocket Integration (Available but not implemented)
```python
# Real-time data streaming
api.start_websocket(
    order_update_callback=order_callback,
    subscribe_callback=feed_callback
)
api.subscribe(['NSE|2885'])  # Live Reliance data
```

#### Trading Operations (API Ready)
```python
# Place orders (requires trading permissions)
ret = api.place_order(
    buy_or_sell='B',
    product_type='C', 
    exchange='NSE',
    tradingsymbol='RELIANCE-EQ',
    quantity=1,
    price_type='LMT',
    price=2500.00
)
```

### 📚 Documentation & Support
- **API Documentation**: https://pi.flattrade.in/docs
- **GitHub Repository**: https://github.com/flattrade/pythonAPI
- **Support Portal**: https://flattrade.in/support/
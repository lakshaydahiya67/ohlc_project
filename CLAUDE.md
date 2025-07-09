# Flattrade API Documentation & Implementation Guide

## Overview
Flattrade provides a free Python API for stock market data and trading. This guide covers fetching OHLC (Open, High, Low, Close) data for stocks with specific time intervals.

## Key Resources
- **GitHub Repository**: https://github.com/flattrade/pythonAPI
- **Official Documentation**: https://pi.flattrade.in/docs
- **Wall Dashboard**: https://wall.flattrade.in (for API key generation)

## Authentication Setup

### 1. Generate API Key and Secret
1. Login to Wall: https://wall.flattrade.in
2. Navigate to "Pi" in top menu bar
3. Click "CREATE NEW API KEY"
4. Enter App Name, App Short Name, and Redirect URL
5. Accept T&C and press "Create" to generate API key and secret

### 2. Token Generation Process
- Token must be generated daily before market open
- Authentication involves SHA-256 hash of: `API_KEY + request_code + API_SECRET`
- Token generation can be automated between 8:30AM to 8:39AM on weekdays

### 3. Session Setup
```python
from api_helper import NorenApiPy

api = NorenApiPy()
usersession = 'your_generated_token'  # Daily token
userid = 'your_user_id'               # Your Flattrade user ID

# Set session
ret = api.set_session(userid=userid, password='', usertoken=usersession)
```

## OHLC Data Endpoints

### 1. `get_time_price_series()` - Intraday Data
Retrieves time-price series data with custom intervals:

```python
import datetime

# Set start time (e.g., start of day)
lastBusDay = datetime.datetime.today()
lastBusDay = lastBusDay.replace(hour=0, minute=0, second=0, microsecond=0)

# Fetch 5-minute interval data
ret = api.get_time_price_series(
    exchange='NSE',
    token='2885',                    # Reliance token
    starttime=lastBusDay.timestamp(),
    interval=5                       # 5-minute intervals
)
```

### 2. `get_daily_price_series()` - Daily Data
Retrieves daily price series data:

```python
ret = api.get_daily_price_series(
    exchange='NSE',
    tradingsymbol='RELIANCE-EQ',
    startdate=0
)
```

### 3. `get_quotes()` - Live Quotes
Provides real-time market quotes:

```python
quotes = api.get_quotes(exchange='NSE', tradingsymbol='RELIANCE-EQ')
```

## Stock Symbol Information

### Reliance Industries Limited
- **Exchange**: NSE
- **Token**: 2885
- **Trading Symbol**: RELIANCE-EQ
- **Series**: EQ (Equity - normal trading segment)

### Finding Stock Tokens
Use `searchscrip()` to find tokens for any stock:

```python
ret = api.searchscrip(exchange='NSE', searchtext='RELIANCE')
```

## Additional Methods

### `get_option_chain()`
Retrieves option chain data for derivatives trading.

### `get_security_info()`
Gets detailed instrument metadata.

### `searchscrip()`
Search for specific instruments or partial matches.

## Response Format
- Success: JSON format with TPData success indication
- Failure: JSON format with error details

## Important Notes

### API Limitations
- Only 1 algo platform can be used at a time with Flattrade accounts
- Multiple API apps can be created, but only 1 api key/secret can be active per day
- Token expires daily and must be regenerated

### Interval Options
Common intervals for `get_time_price_series()`:
- 1 = 1 minute
- 3 = 3 minutes
- 5 = 5 minutes
- 15 = 15 minutes
- 30 = 30 minutes
- 60 = 1 hour

### EQ Series Explained
The "-EQ" suffix indicates:
- Normal equity trading segment
- Allows intraday and delivery-based trades
- Supports short selling and BTST (Buy Today Sell Tomorrow)
- Most common trading category for regular stock transactions

## Sample Implementation for Django

### Basic Structure
```python
# flattrade_client.py
import datetime
from api_helper import NorenApiPy

class FlattradeClient:
    def __init__(self, userid, token):
        self.api = NorenApiPy()
        self.userid = userid
        self.token = token
        self.setup_session()
    
    def setup_session(self):
        ret = self.api.set_session(
            userid=self.userid,
            password='',
            usertoken=self.token
        )
        return ret
    
    def get_reliance_ohlc_5min(self):
        """Fetch Reliance OHLC data with 5-minute intervals"""
        lastBusDay = datetime.datetime.today()
        lastBusDay = lastBusDay.replace(hour=0, minute=0, second=0, microsecond=0)
        
        return self.api.get_time_price_series(
            exchange='NSE',
            token='2885',  # Reliance token
            starttime=lastBusDay.timestamp(),
            interval=5
        )
```

## Next Steps
1. Set up Django project structure
2. Install required dependencies
3. Implement token generation automation
4. Create views for displaying OHLC data
5. Add error handling and logging
6. Test with live market data

## Support
- Visit: https://flattrade.in/support/
- Documentation: https://pi.flattrade.in/docs
- GitHub Issues: https://github.com/flattrade/pythonAPI/issues
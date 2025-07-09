"""
Credentials Template for Flattrade API
=====================================

Instructions:
1. Copy this file to 'credentials.py'
2. Fill in your actual credentials
3. Import and use in your main scripts

To get your credentials:
1. Go to https://wall.flattrade.in
2. Login with your Flattrade account
3. Click on "Pi" in the top menu
4. Click "CREATE NEW API KEY"
5. Fill in the details and create your API key

Important Notes:
- Token expires daily and needs to be regenerated
- Keep your credentials secure and never commit them to version control
- Add credentials.py to your .gitignore file
"""

# Your Flattrade User ID (usually starts with 'FT')
USER_ID = "YOUR_USER_ID_HERE"

# Your daily generated token
# This needs to be updated every day before market hours
TOKEN = "YOUR_DAILY_TOKEN_HERE"

# Your API Key (needed for token generation)
API_KEY = "YOUR_API_KEY_HERE"

# Your API Secret (needed for token generation)
API_SECRET = "YOUR_API_SECRET_HERE"

# Example of how to use these credentials:
"""
from credentials import USER_ID, TOKEN
from flattrade_client import FlattradeClient

client = FlattradeClient(USER_ID, TOKEN)
client.setup_session()
"""
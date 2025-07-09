"""
Flattrade API Token Generator
============================

This script helps you generate the daily token needed for the Flattrade API.
Token generation involves a 2-step process:
1. Get authorization code from Flattrade
2. Generate token using SHA256 hash

Run this script daily before market hours to get your token.
"""

import hashlib
import requests
import webbrowser
import urllib.parse

class FlattradeTokenGenerator:
    def __init__(self, api_key, api_secret):
        """
        Initialize token generator with API credentials
        
        Args:
            api_key (str): Your Flattrade API Key
            api_secret (str): Your Flattrade API Secret
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://authapi.flattrade.in/trade/apitoken"
        self.auth_url = f"https://auth.flattrade.in/?app_key={api_key}"
    
    def step1_get_authorization_code(self):
        """
        Step 1: Get authorization code from Flattrade
        This opens a browser window for manual authentication
        """
        print("🔐 Step 1: Getting Authorization Code")
        print("="*50)
        print(f"Opening browser to: {self.auth_url}")
        print("\nInstructions:")
        print("1. Browser will open to Flattrade login page")
        print("2. Login with your Flattrade credentials")
        print("3. After login, you'll be redirected to a URL")
        print("4. Copy the 'request_code' parameter from the redirect URL")
        print("5. The URL will look like: https://127.0.0.1:8080/?request_code=XXXXXX")
        print("\nOpening browser...")
        
        # Open browser for manual authentication
        webbrowser.open(self.auth_url)
        
        # Get request code from user
        request_code = input("\n📋 Enter the request_code from the redirect URL: ").strip()
        
        if not request_code:
            print("❌ Request code is required!")
            return None
        
        return request_code
    
    def step2_generate_token(self, request_code):
        """
        Step 2: Generate token using SHA256 hash
        
        Args:
            request_code (str): Authorization code from step 1
            
        Returns:
            str: Generated token or None if failed
        """
        print("\n🔑 Step 2: Generating Token")
        print("="*50)
        
        try:
            # Create SHA256 hash: API_KEY + request_code + API_SECRET
            hash_string = self.api_key + request_code + self.api_secret
            hash_value = hashlib.sha256(hash_string.encode()).hexdigest()
            
            print(f"📝 Hash string: {self.api_key} + {request_code} + {self.api_secret[:4]}...")
            print(f"🔐 Generated hash: {hash_value[:10]}...")
            
            # Prepare payload
            payload = {
                "api_key": self.api_key,
                "request_code": request_code,
                "api_secret": hash_value
            }
            
            # Make API request to generate token
            print("📡 Sending request to Flattrade API...")
            response = requests.post(self.base_url, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('stat') == 'Ok':
                    token = data.get('token')
                    user_id = data.get('userid')
                    
                    print("✅ Token generated successfully!")
                    print(f"👤 User ID: {user_id}")
                    print(f"🎟️  Token: {token}")
                    
                    # Save token to file for easy access
                    with open('daily_token.txt', 'w') as f:
                        f.write(f"USER_ID = \"{user_id}\"\n")
                        f.write(f"TOKEN = \"{token}\"\n")
                        f.write(f"# Generated on: {requests.utils.default_headers()}\n")
                    
                    print("💾 Token saved to 'daily_token.txt'")
                    return token
                else:
                    print(f"❌ Token generation failed: {data}")
                    return None
            else:
                print(f"❌ HTTP Error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error generating token: {e}")
            return None
    
    def generate_token(self):
        """
        Complete token generation process
        
        Returns:
            str: Generated token or None if failed
        """
        print("🚀 Flattrade Token Generator")
        print("="*50)
        
        # Step 1: Get authorization code
        request_code = self.step1_get_authorization_code()
        
        if not request_code:
            return None
        
        # Step 2: Generate token
        token = self.step2_generate_token(request_code)
        
        if token:
            print("\n🎉 Token generation completed successfully!")
            print("\n📋 Next steps:")
            print("1. Copy the token from above")
            print("2. Update your credentials.py file")
            print("3. Run your trading scripts")
            print("\n⏰ Remember: Token expires daily, run this script every day!")
        
        return token

def main():
    """
    Main function to run token generation
    """
    print("Please enter your Flattrade API credentials:")
    api_key = input("🔑 API Key: ").strip()
    api_secret = input("🔐 API Secret: ").strip()
    
    if not api_key or not api_secret:
        print("❌ Both API Key and API Secret are required!")
        return
    
    # Create token generator
    generator = FlattradeTokenGenerator(api_key, api_secret)
    
    # Generate token
    token = generator.generate_token()
    
    if token:
        print(f"\n✅ Your daily token is: {token}")
    else:
        print("\n❌ Token generation failed!")

if __name__ == "__main__":
    main()
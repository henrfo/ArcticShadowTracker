#!/usr/bin/env python3
"""
BarentsWatch Official Norwegian Arctic AIS API Authentication
Provides OAuth2 client_credentials authentication for legitimate Arctic surveillance.
"""

import requests
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from pathlib import Path
import os

logger = logging.getLogger(__name__)

class BarentsWatchAuth:
    """
    Official Norwegian BarentsWatch API authentication handler.
    Provides legitimate access to Norwegian Arctic AIS data.
    """
    
    def __init__(self):
        """Initialize BarentsWatch authentication."""
        # Official API endpoints
        self.auth_url = "https://id.barentswatch.no/connect/token"
        self.base_url = "https://www.barentswatch.no/bwapi/v1/"
        
        # OAuth2 client credentials
        self.client_id = "henrikformoe@gmail.com:ArcticShadowTracker"
        self.client_id_encoded = "henrikformoe%40gmail.com%3AArcticShadowTracker"
        self.grant_type = "client_credentials"
        self.scope = "api"
        
        # Token management
        self.access_token = None
        self.token_expires_at = None
        self.token_type = "Bearer"
        
        logger.info("BarentsWatch authentication initialized")
    
    def authenticate(self) -> bool:
        """
        Authenticate with BarentsWatch OAuth2 service.
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        logger.info("Authenticating with BarentsWatch OAuth2...")
        
        # Check for existing valid token
        if self.is_token_valid():
            logger.info("Using existing valid token")
            return True
        
        # Get client secret from environment or config
        client_secret = self._get_client_secret()
        if not client_secret:
            logger.error("BarentsWatch client secret not found")
            logger.info("Please set environment variable: BARENTSWATCH_CLIENT_SECRET")
            return False
        
        # OAuth2 client_credentials request
        auth_data = {
            'client_id': self.client_id,
            'client_secret': client_secret,
            'grant_type': self.grant_type,
            'scope': self.scope
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'ArcticShadowTracker/1.0 (Arctic Maritime Surveillance)'
        }
        
        try:
            response = requests.post(
                self.auth_url,
                data=auth_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                token_data = response.json()
                
                # Extract token information
                self.access_token = token_data.get('access_token')
                expires_in = token_data.get('expires_in', 3600)  # Default 1 hour
                self.token_type = token_data.get('token_type', 'Bearer')
                
                # Calculate expiration time (with 5 minute buffer)
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
                
                logger.info(f"BarentsWatch authentication successful")
                logger.info(f"Token expires at: {self.token_expires_at}")
                
                # Cache token for reuse
                self._cache_token(token_data)
                
                return True
            
            else:
                logger.error(f"BarentsWatch auth failed: {response.status_code} {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"BarentsWatch authentication error: {e}")
            return False
    
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for API requests.
        
        Returns:
            Dict containing Authorization header
        """
        if not self.is_token_valid():
            if not self.authenticate():
                raise Exception("Cannot authenticate with BarentsWatch")
        
        return {
            'Authorization': f'{self.token_type} {self.access_token}',
            'Content-Type': 'application/json',
            'User-Agent': 'ArcticShadowTracker/1.0 (Arctic Maritime Surveillance)'
        }
    
    def is_token_valid(self) -> bool:
        """Check if current token is valid and not expired."""
        if not self.access_token or not self.token_expires_at:
            return False
        
        return datetime.now() < self.token_expires_at
    
    def _get_client_secret(self) -> Optional[str]:
        """Get BarentsWatch client secret from environment or config."""
        # Try environment variable first
        secret = os.getenv('BARENTSWATCH_CLIENT_SECRET')
        if secret:
            return secret
        
        # Try config file
        config_file = Path('config/barentswatch_config.json')
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                return config.get('client_secret')
            except Exception as e:
                logger.warning(f"Failed to read BarentsWatch config: {e}")
        
        # Instructions for setup
        logger.info("🔑 BarentsWatch API Setup Required:")
        logger.info("1. Visit: https://developer.barentswatch.no/")
        logger.info("2. Register your application") 
        logger.info("3. Use Client ID: henrikformoe@gmail.com:ArcticShadowTracker")
        logger.info("4. Set environment variable: export BARENTSWATCH_CLIENT_SECRET='your_secret'")
        
        return None
    
    def _cache_token(self, token_data: Dict):
        """Cache token data for reuse."""
        try:
            cache_dir = Path('data/auth_cache')
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            cache_file = cache_dir / 'barentswatch_token.json'
            
            cache_data = {
                'access_token': token_data.get('access_token'),
                'token_type': token_data.get('token_type', 'Bearer'),
                'expires_at': self.token_expires_at.isoformat(),
                'cached_at': datetime.now().isoformat()
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            logger.debug(f"Token cached to {cache_file}")
            
        except Exception as e:
            logger.warning(f"Failed to cache token: {e}")
    
    def _load_cached_token(self) -> bool:
        """Load cached token if available and valid."""
        try:
            cache_file = Path('data/auth_cache/barentswatch_token.json')
            
            if not cache_file.exists():
                return False
            
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Check if cached token is still valid
            expires_at = datetime.fromisoformat(cache_data.get('expires_at'))
            
            if datetime.now() < expires_at:
                self.access_token = cache_data.get('access_token')
                self.token_type = cache_data.get('token_type', 'Bearer')
                self.token_expires_at = expires_at
                
                logger.info("Loaded valid cached BarentsWatch token")
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Failed to load cached token: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test BarentsWatch API connection."""
        logger.info("Testing BarentsWatch API connection...")
        
        try:
            if not self.authenticate():
                return False
            
            # Test API endpoint
            test_url = f"{self.base_url}geodata/ais"
            headers = self.get_auth_headers()
            
            # Small bounding box test for Svalbard
            params = {
                'bbox': '10,78,20,79',  # Small Svalbard area
                'limit': 1
            }
            
            response = requests.get(
                test_url,
                headers=headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"BarentsWatch API test successful")
                logger.info(f"Response type: {type(data)}")
                return True
            else:
                logger.error(f"BarentsWatch API test failed: {response.status_code} {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"BarentsWatch connection test failed: {e}")
            return False

# Test function
def test_barentswatch_auth():
    """Test BarentsWatch authentication."""
    print("🇳🇴 Testing BarentsWatch Official Norwegian Arctic AIS Authentication")
    print("=" * 70)
    
    auth = BarentsWatchAuth()
    
    # Test authentication
    print("🔑 Testing OAuth2 authentication...")
    if auth.authenticate():
        print("   ✅ Authentication successful")
        print(f"   🎫 Token expires at: {auth.token_expires_at}")
        
        # Test API connection
        print("\n🔍 Testing API connection...")
        if auth.test_connection():
            print("   ✅ API connection successful")
            print("   🌊 Ready for Arctic AIS data collection")
        else:
            print("   ❌ API connection failed")
    else:
        print("   ❌ Authentication failed")
        print("\n💡 Setup instructions:")
        print("1. Visit: https://developer.barentswatch.no/")
        print("2. Register application with Client ID: henrikformoe@gmail.com:ArcticShadowTracker")
        print("3. Set environment variable: export BARENTSWATCH_CLIENT_SECRET='your_secret'")

if __name__ == "__main__":
    test_barentswatch_auth()
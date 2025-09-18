#!/usr/bin/env python3
"""
Arctic Shadow Tracker - API Management and Failover
Handles rate limiting, failover, and circuit breaker patterns for external APIs.
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import aiohttp
import backoff
from datetime import datetime, timedelta
import redis
import json

logger = logging.getLogger(__name__)

class APIStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    CIRCUIT_OPEN = "circuit_open"

@dataclass
class APIEndpoint:
    name: str
    url: str
    priority: int  # 1 = primary, 2 = secondary, etc.
    rate_limit_per_minute: int
    timeout_seconds: int
    api_key: Optional[str] = None
    headers: Optional[Dict[str, str]] = None

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    half_open_max_calls: int = 3

class APIManager:
    """Manages external API calls with rate limiting, failover, and circuit breaker patterns"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.endpoints: Dict[str, List[APIEndpoint]] = {}
        self.circuit_breakers: Dict[str, CircuitBreakerConfig] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Initialize API endpoints
        self._setup_endpoints()
        
    def _setup_endpoints(self):
        """Setup API endpoints with failover configuration"""
        
        # Copernicus Data Space Ecosystem endpoints
        self.endpoints['copernicus'] = [
            APIEndpoint(
                name="copernicus_primary",
                url="https://catalogue.dataspace.copernicus.eu",
                priority=1,
                rate_limit_per_minute=60,
                timeout_seconds=30,
                headers={"User-Agent": "ArcticShadowTracker/1.0"}
            ),
            APIEndpoint(
                name="copernicus_backup",
                url="https://scihub.copernicus.eu",
                priority=2,
                rate_limit_per_minute=30,
                timeout_seconds=45,
                headers={"User-Agent": "ArcticShadowTracker/1.0"}
            )
        ]
        
        # AIS data sources with multiple providers
        self.endpoints['ais'] = [
            APIEndpoint(
                name="aishub_primary",
                url="http://data.aishub.net/ws.php",
                priority=1,
                rate_limit_per_minute=100,
                timeout_seconds=20
            ),
            APIEndpoint(
                name="marinetraffic_backup",
                url="https://services.marinetraffic.com/api",
                priority=2,
                rate_limit_per_minute=50,
                timeout_seconds=25,
                api_key="MARINE_TRAFFIC_API_KEY"
            ),
            APIEndpoint(
                name="vesselfinder_backup",
                url="https://api.vesselfinder.com",
                priority=3,
                rate_limit_per_minute=30,
                timeout_seconds=30,
                api_key="VESSELFINDER_API_KEY"
            )
        ]
        
        # Weather data for environmental context
        self.endpoints['weather'] = [
            APIEndpoint(
                name="met_norway",
                url="https://api.met.no/weatherapi",
                priority=1,
                rate_limit_per_minute=200,
                timeout_seconds=15,
                headers={"User-Agent": "ArcticShadowTracker/1.0"}
            ),
            APIEndpoint(
                name="openweather_backup",
                url="https://api.openweathermap.org/data/2.5",
                priority=2,
                rate_limit_per_minute=60,
                timeout_seconds=20,
                api_key="OPENWEATHER_API_KEY"
            )
        ]
        
        # Setup circuit breakers for each service
        for service in self.endpoints.keys():
            self.circuit_breakers[service] = CircuitBreakerConfig()
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            connector=aiohttp.TCPConnector(limit=20, limit_per_host=5)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def _get_rate_limit_key(self, endpoint: APIEndpoint) -> str:
        """Generate Redis key for rate limiting"""
        return f"rate_limit:{endpoint.name}:{int(time.time() // 60)}"
    
    def _get_circuit_breaker_key(self, service: str) -> str:
        """Generate Redis key for circuit breaker state"""
        return f"circuit_breaker:{service}"
    
    async def _check_rate_limit(self, endpoint: APIEndpoint) -> bool:
        """Check if API call is within rate limits"""
        key = self._get_rate_limit_key(endpoint)
        current_calls = self.redis.get(key)
        
        if current_calls is None:
            # First call in this minute
            self.redis.setex(key, 60, 1)
            return True
        
        if int(current_calls) >= endpoint.rate_limit_per_minute:
            logger.warning(f"Rate limit exceeded for {endpoint.name}")
            return False
        
        # Increment counter
        self.redis.incr(key)
        return True
    
    async def _get_circuit_breaker_state(self, service: str) -> APIStatus:
        """Get current circuit breaker state"""
        key = self._get_circuit_breaker_key(service)
        state_data = self.redis.get(key)
        
        if state_data is None:
            return APIStatus.HEALTHY
        
        try:
            state = json.loads(state_data)
            current_time = datetime.now().timestamp()
            
            if state['status'] == APIStatus.CIRCUIT_OPEN.value:
                # Check if recovery timeout has passed
                if current_time - state['opened_at'] > self.circuit_breakers[service].recovery_timeout:
                    # Transition to half-open
                    state['status'] = APIStatus.DEGRADED.value
                    state['half_open_calls'] = 0
                    self.redis.setex(key, 300, json.dumps(state))
                    return APIStatus.DEGRADED
                return APIStatus.CIRCUIT_OPEN
            
            return APIStatus(state['status'])
        except (json.JSONDecodeError, KeyError):
            return APIStatus.HEALTHY
    
    async def _record_api_call_result(self, service: str, success: bool):
        """Record API call result for circuit breaker logic"""
        key = self._get_circuit_breaker_key(service)
        state_data = self.redis.get(key)
        
        if state_data is None:
            state = {
                'status': APIStatus.HEALTHY.value,
                'failure_count': 0,
                'last_failure': None,
                'half_open_calls': 0
            }
        else:
            state = json.loads(state_data)
        
        current_time = datetime.now().timestamp()
        config = self.circuit_breakers[service]
        
        if success:
            if state['status'] == APIStatus.DEGRADED.value:
                # In half-open state, successful call
                state['half_open_calls'] += 1
                if state['half_open_calls'] >= config.half_open_max_calls:
                    # Successful recovery
                    state['status'] = APIStatus.HEALTHY.value
                    state['failure_count'] = 0
                    logger.info(f"Circuit breaker closed for {service}")
            else:
                # Reset failure count on success
                state['failure_count'] = 0
        else:
            # Record failure
            state['failure_count'] += 1
            state['last_failure'] = current_time
            
            if state['failure_count'] >= config.failure_threshold:
                # Open circuit breaker
                state['status'] = APIStatus.CIRCUIT_OPEN.value
                state['opened_at'] = current_time
                logger.error(f"Circuit breaker opened for {service} after {state['failure_count']} failures")
        
        # Store updated state
        self.redis.setex(key, 300, json.dumps(state))
    
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
        max_time=30
    )
    async def _make_api_call(self, endpoint: APIEndpoint, path: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make API call with retries"""
        if not self.session:
            raise RuntimeError("API Manager not initialized as async context manager")
        
        # Prepare headers
        headers = endpoint.headers.copy() if endpoint.headers else {}
        if endpoint.api_key:
            headers['Authorization'] = f'Bearer {endpoint.api_key}'
        
        # Prepare URL and parameters
        url = f"{endpoint.url.rstrip('/')}/{path.lstrip('/')}"
        if endpoint.api_key and 'api_key' not in params:
            params['api_key'] = endpoint.api_key
        
        try:
            async with self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=endpoint.timeout_seconds)
            ) as response:
                response.raise_for_status()
                
                # Handle different content types
                content_type = response.headers.get('content-type', '').lower()
                if 'application/json' in content_type:
                    return await response.json()
                elif 'application/xml' in content_type or 'text/xml' in content_type:
                    # For XML responses (some satellite APIs)
                    text = await response.text()
                    return {'xml_content': text}
                else:
                    text = await response.text()
                    return {'text_content': text}
                    
        except aiohttp.ClientResponseError as e:
            logger.error(f"API call failed for {endpoint.name}: HTTP {e.status}")
            raise
        except asyncio.TimeoutError:
            logger.error(f"API call timeout for {endpoint.name}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error for {endpoint.name}: {e}")
            raise
    
    async def call_api(self, service: str, path: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Make API call with automatic failover and circuit breaker protection
        
        Args:
            service: Service name (e.g., 'copernicus', 'ais', 'weather')
            path: API endpoint path
            params: Query parameters
            
        Returns:
            API response data or None if all endpoints failed
        """
        if service not in self.endpoints:
            raise ValueError(f"Unknown service: {service}")
        
        # Check circuit breaker status
        circuit_status = await self._get_circuit_breaker_state(service)
        if circuit_status == APIStatus.CIRCUIT_OPEN:
            logger.warning(f"Circuit breaker open for {service}, skipping API call")
            return None
        
        # Try endpoints in priority order
        endpoints = sorted(self.endpoints[service], key=lambda x: x.priority)
        last_exception = None
        
        for endpoint in endpoints:
            # Check rate limits
            if not await self._check_rate_limit(endpoint):
                continue
            
            try:
                logger.debug(f"Trying API call to {endpoint.name}")
                result = await self._make_api_call(endpoint, path, params)
                
                # Record successful call
                await self._record_api_call_result(service, True)
                
                logger.info(f"Successful API call to {endpoint.name}")
                return result
                
            except Exception as e:
                last_exception = e
                logger.warning(f"API call failed for {endpoint.name}: {e}")
                
                # Record failed call
                await self._record_api_call_result(service, False)
                
                # Continue to next endpoint
                continue
        
        # All endpoints failed
        logger.error(f"All endpoints failed for service {service}. Last error: {last_exception}")
        return None
    
    async def get_api_health_status(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all API services"""
        status = {}
        
        for service in self.endpoints.keys():
            circuit_status = await self._get_circuit_breaker_state(service)
            
            # Check rate limit usage for each endpoint
            endpoint_status = []
            for endpoint in self.endpoints[service]:
                rate_key = self._get_rate_limit_key(endpoint)
                current_calls = self.redis.get(rate_key)
                rate_usage = int(current_calls or 0)
                
                endpoint_status.append({
                    'name': endpoint.name,
                    'priority': endpoint.priority,
                    'rate_limit_usage': f"{rate_usage}/{endpoint.rate_limit_per_minute}",
                    'rate_limit_percent': (rate_usage / endpoint.rate_limit_per_minute) * 100
                })
            
            status[service] = {
                'circuit_status': circuit_status.value,
                'endpoints': endpoint_status
            }
        
        return status

# Usage example for integration
async def example_usage():
    """Example of how to use the API Manager"""
    import redis.asyncio as redis
    
    # Initialize Redis client
    redis_client = redis.from_url("redis://localhost:6379")
    
    async with APIManager(redis_client) as api_manager:
        # Fetch AIS data with automatic failover
        ais_data = await api_manager.call_api(
            service='ais',
            path='ws.php',
            params={
                'username': 'DH_DEMO',
                'format': '1',
                'output': 'json',
                'compress': '0',
                'latmin': '69.0',
                'latmax': '82.0',
                'lonmin': '5.0',
                'lonmax': '35.0'
            }
        )
        
        # Check API health
        health_status = await api_manager.get_api_health_status()
        print(f"API Health Status: {health_status}")
        
        return ais_data
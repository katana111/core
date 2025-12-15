"""
Proxy Configuration Module
Manages proxy rotation to avoid IP blocking
"""

import random
from typing import Optional, List, Dict
import requests
from datetime import datetime, timedelta


class ProxyManager:
    """Manages proxy rotation for web scraping"""
    
    def __init__(self, proxies: Optional[List[str]] = None):
        """
        Initialize proxy manager
        
        Args:
            proxies: List of proxy URLs in format 'http://user:pass@host:port' or 'http://host:port'
        """
        self.proxies = proxies or []
        self.failed_proxies = set()
        self.proxy_stats = {}  # Track success/failure rates
        
    def add_proxy(self, proxy: str):
        """Add a proxy to the pool"""
        if proxy not in self.proxies:
            self.proxies.append(proxy)
            
    def add_proxies(self, proxies: List[str]):
        """Add multiple proxies to the pool"""
        for proxy in proxies:
            self.add_proxy(proxy)
    
    def get_proxy(self) -> Optional[Dict[str, str]]:
        """
        Get a random working proxy
        
        Returns:
            Dict with 'http' and 'https' proxy URLs, or None if no proxies available
        """
        available_proxies = [p for p in self.proxies if p not in self.failed_proxies]
        
        if not available_proxies:
            # Reset failed proxies if all have failed
            if self.failed_proxies:
                print("All proxies failed, resetting failed list...")
                self.failed_proxies.clear()
                available_proxies = self.proxies
            else:
                return None
        
        proxy = random.choice(available_proxies)
        return {
            'http': proxy,
            'https': proxy
        }
    
    def mark_proxy_failed(self, proxy_dict: Dict[str, str]):
        """Mark a proxy as failed"""
        if proxy_dict and 'http' in proxy_dict:
            proxy = proxy_dict['http']
            self.failed_proxies.add(proxy)
            print(f"Marked proxy as failed: {proxy}")
    
    def mark_proxy_success(self, proxy_dict: Dict[str, str]):
        """Mark a proxy as successful (remove from failed list if present)"""
        if proxy_dict and 'http' in proxy_dict:
            proxy = proxy_dict['http']
            if proxy in self.failed_proxies:
                self.failed_proxies.remove(proxy)
    
    def test_proxy(self, proxy: str, test_url: str = "https://httpbin.org/ip") -> bool:
        """
        Test if a proxy is working
        
        Args:
            proxy: Proxy URL
            test_url: URL to test the proxy with
            
        Returns:
            True if proxy works, False otherwise
        """
        try:
            proxies = {'http': proxy, 'https': proxy}
            response = requests.get(test_url, proxies=proxies, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Proxy test failed for {proxy}: {str(e)}")
            return False
    
    def get_stats(self) -> Dict:
        """Get proxy statistics"""
        return {
            'total_proxies': len(self.proxies),
            'failed_proxies': len(self.failed_proxies),
            'available_proxies': len(self.proxies) - len(self.failed_proxies)
        }


# Free proxy sources (for testing - not recommended for production)
FREE_PROXY_SOURCES = [
    "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
]


def get_free_proxies(limit: int = 10) -> List[str]:
    """
    Fetch free proxies (for testing purposes)
    Note: Free proxies are unreliable, use paid proxies for production
    
    Args:
        limit: Maximum number of proxies to return
        
    Returns:
        List of proxy URLs
    """
    proxies = []
    
    try:
        response = requests.get(FREE_PROXY_SOURCES[0], timeout=10)
        if response.status_code == 200:
            proxy_list = response.text.strip().split('\n')
            for proxy in proxy_list[:limit]:
                if proxy.strip():
                    proxies.append(f"http://{proxy.strip()}")
    except Exception as e:
        print(f"Failed to fetch free proxies: {str(e)}")
    
    return proxies


# Example premium proxy services (you need to sign up and get credentials)
PREMIUM_PROXY_EXAMPLES = {
    'brightdata': 'http://username:password@brd.superproxy.io:22225',
    'oxylabs': 'http://username:password@pr.oxylabs.io:7777',
    'smartproxy': 'http://username:password@gate.smartproxy.com:7000',
    'proxy6': 'http://username:password@proxy6.net:1080',
}


def get_proxy_manager_with_free_proxies(limit: int = 10) -> ProxyManager:
    """
    Create a ProxyManager with free proxies
    Note: For production, use paid proxy services
    
    Args:
        limit: Number of free proxies to fetch
        
    Returns:
        ProxyManager instance
    """
    manager = ProxyManager()
    free_proxies = get_free_proxies(limit)
    manager.add_proxies(free_proxies)
    return manager

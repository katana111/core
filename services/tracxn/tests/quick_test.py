#!/usr/bin/env python3
"""Quick test to verify scraper setup is working"""

print("Testing Tracxn Scraper...")
print("=" * 60)

# Test imports
print("\n1. Testing imports...")
try:
    from scraper import TracxnScraper
    from proxy_config import ProxyManager
    print("   ✅ Imports successful")
except ImportError as e:
    print(f"   ❌ Import failed: {e}")
    exit(1)

# Test Playwright
print("\n2. Testing Playwright installation...")
try:
    from playwright.sync_api import sync_playwright
    print("   ✅ Playwright imported")
except ImportError as e:
    print(f"   ❌ Playwright not installed: {e}")
    exit(1)

# Test browser launch
print("\n3. Testing browser launch...")
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        browser.close()
    print("   ✅ Browser launched successfully")
except Exception as e:
    print(f"   ❌ Browser launch failed: {e}")
    exit(1)

# Test scraper initialization
print("\n4. Testing scraper initialization...")
try:
    scraper = TracxnScraper(headless=True)
    print("   ✅ Scraper initialized")
    print(f"   📁 Output file: {scraper.output_file}")
except Exception as e:
    print(f"   ❌ Scraper initialization failed: {e}")
    exit(1)

# Test proxy manager
print("\n5. Testing proxy manager...")
try:
    proxy_manager = ProxyManager(['http://test:test@proxy.example.com:8000'])
    print("   ✅ Proxy manager initialized")
    stats = proxy_manager.get_stats()
    print(f"   📊 Proxy stats: {stats}")
except Exception as e:
    print(f"   ❌ Proxy manager failed: {e}")
    exit(1)

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED!")
print("=" * 60)
print("\nYou can now run:")
print("  python3 example_usage.py  # Full scraping example")
print("  python3 test_scraper.py   # Test with SEON company")

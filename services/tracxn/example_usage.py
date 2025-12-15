"""
Tracxn Service - Example Usage
Demonstrates how to use the Tracxn scraper with proxy support and database integration
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from scraper import TracxnScraper
from proxy_config import ProxyManager
from database import get_db


def example_without_proxy():
    """Example: Scraping without proxy (not recommended for multiple requests)"""
    print("Example 1: Scraping without proxy + Database saving")
    print("-" * 60)
    
    # Initialize centralized database connection
    db = get_db()
    db.initialize()  # Uses environment variables or defaults
    
    # Create scraper with database enabled
    scraper = TracxnScraper(
        headless=False,
        save_to_db=True  # Enable database saving
    )
    
    # Example company URL - SEON company
    company_url = "https://tracxn.com/d/companies/seon/__XX9gJBOrnKi_U527Or0hGsnVj2ivM2SwtgE34ahHgMo"
    
    # Scrape with provided company name (optional)
    result = scraper.scrape_company(company_url, company_name="SEON")
    
    if result:
        print(f"\n{'='*60}")
        print(f"SCRAPED DATA FOR: {result['company_name']}")
        print(f"{'='*60}")
        print(f"Founded Year: {result['founded_year']}")
        print(f"Location: {result['location']}")
        print(f"Main Office: {result['main_office']}")
        print(f"Registered Address: {result['registered_address']}")
        print(f"Funding Stage: {result['funding_stage']}")
        print(f"Total Funding: {result['fundings']['total_funding']}")
        print(f"Latest Funding: {result['fundings']['latest_funding_round']}")
        print(f"Employee Count: {result['employee_count']}")
        print(f"Exit Details: {result['exit_details']}")
        print(f"Investors: {len(result['fundings'].get('investors', []))}")
        print(f"Acquisitions: {len(result['acquisitions'])}")
        print(f"Investments: {len(result['investments'])}")
        print(f"Funding Rounds: {len(result['fundings']['funding_rounds'])}")
        
        if 'db_competitor_id' in result:
            print(f"\n✅ Saved to database with ID: {result['db_competitor_id']}")
        else:
            print(f"\n❌ Not saved to database")
        print(f"{'='*60}")
    else:
        print("Failed to scrape company data")


def example_with_manual_proxies():
    """Example: Scraping with manually configured proxies + Database"""
    print("\n\nExample 2: Scraping with manual proxy configuration + Database")
    print("-" * 60)
    
    # Configure your proxies here
    # Format: 'http://username:password@host:port' or 'http://host:port'
    proxies = [
        # Add your proxy URLs here
        # Examples:
        # 'http://user:pass@proxy1.example.com:8080',
        # 'http://user:pass@proxy2.example.com:8080',
        # 'http://user:pass@proxy3.example.com:8080',
        'http://insider_wOhFv:yAu_kjidArup78+@c.oxylabs.io:8000',
    ]
    
    # Create proxy manager
    proxy_manager = ProxyManager(proxies)
    
    # Initialize centralized database connection
    db = get_db()
    db.initialize()
    
    # Create scraper with proxy support AND database
    scraper = TracxnScraper(
        proxy_manager=proxy_manager,
        headless=False,
        save_to_db=True  # Enable database saving
    )
    
    # List of company URLs to scrape
    company_urls = [
        "https://tracxn.com/d/legal-entities/india/monnai-technology-india-private-limited/__At2D6zYf_F_39L9w9944dgtHpBOKvKPO2BiHSt-wOOM",
        # Add more company URLs
    ]
    
    # Optional: Provide company names (must match length of URLs)
    company_names = [
        "Monnai",
        # Add more company names
    ]
    
    # Scrape multiple companies (proxy will rotate automatically)
    # Pass company_names to use provided names instead of extracting from page
    results = scraper.scrape_companies(company_urls, company_names=company_names)
    
    print(f"\n\nScraped {len(results)} companies successfully")
    print(f"Results saved to: {scraper.output_file}")
    
    # Show database save count
    db_saved = sum(1 for r in results if 'db_competitor_id' in r)
    print(f"✅ Saved to database: {db_saved}/{len(results)} companies")


def example_with_free_proxies():
    """Example: Scraping with free proxies (testing only, not reliable)"""
    print("\n\nExample 3: Scraping with free proxies (for testing)")
    print("-" * 60)
    print("Note: Free proxies are unreliable. Use paid proxies for production.")
    
    from proxy_config import get_proxy_manager_with_free_proxies
    
    # Get proxy manager with free proxies
    proxy_manager = get_proxy_manager_with_free_proxies(limit=20)
    
    print(f"Loaded {len(proxy_manager.proxies)} free proxies")
    
    if not proxy_manager.proxies:
        print("Could not fetch free proxies. Proceeding without proxy.")
        proxy_manager = None
    
    scraper = TracxnScraper(proxy_manager=proxy_manager, headless=True)
    
    company_url = "https://tracxn.com/d/companies/openai"
    result = scraper.scrape_company(company_url)
    
    if result:
        print(f"\nSuccessfully scraped: {result['company_name']}")
    
    if proxy_manager:
        stats = proxy_manager.get_stats()
        print(f"\nProxy Stats: {stats}")


def example_custom_search():
    """Example: Scrape specific companies with custom configuration"""
    print("\n\nExample 4: Custom company search")
    print("-" * 60)
    
    # Configure with your proxies
    proxies = [
        # Add your proxies here
    ]
    
    proxy_manager = ProxyManager(proxies) if proxies else None
    scraper = TracxnScraper(proxy_manager=proxy_manager, headless=True)
    
    # Custom list of companies to scrape
    companies_to_scrape = [
        "https://tracxn.com/d/companies/company-name-1",
        "https://tracxn.com/d/companies/company-name-2",
        # Add more URLs
    ]
    
    print(f"Scraping {len(companies_to_scrape)} companies...")
    results = scraper.scrape_companies(companies_to_scrape)
    
    # Display summary
    print(f"\n{'='*60}")
    print("SCRAPING SUMMARY")
    print(f"{'='*60}")
    
    for result in results:
        print(f"\nCompany: {result['company_name']}")
        print(f"  Location: {result['location']}")
        print(f"  Founded: {result['founded_year']}")
        print(f"  Employees: {result['employee_count']}")
        print(f"  Funding Stage: {result['funding_stage']}")
        print(f"  Total Funding: {result['fundings'].get('total_funding', 'N/A')}")
        
        if result['fundings'].get('investors'):
            print(f"  Investors: {', '.join(result['fundings']['investors'][:5])}...")
        
        if result['exit_details']:
            print(f"  Exit: {result['exit_details']}")
        
        if result['acquisitions']:
            print(f"  Acquisitions: {len(result['acquisitions'])}")
        
        if result['investments']:
            print(f"  Investments: {len(result['investments'])}")


if __name__ == "__main__":
    # Choose which example to run:
    
    # Example 1: Without proxy (single request) - Good for testing
    example_without_proxy()
    
    # Example 2: With manual proxy configuration (recommended for production)
    # example_with_manual_proxies()
    
    # Example 3: With free proxies (testing only)
    # example_with_free_proxies()
    
    # Example 4: Custom search
    # example_custom_search()

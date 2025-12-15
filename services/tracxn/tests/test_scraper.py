"""
Quick Test Script for Tracxn Scraper
Tests the scraper with SEON company example
"""

import sys
import os
import json

# Add current directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper import TracxnScraper
from proxy_config import ProxyManager


def test_scraper():
    """Test the scraper with SEON company"""
    print("="*70)
    print("TRACXN SCRAPER TEST - SEON Company")
    print("="*70)
    
    # Initialize scraper without proxy for testing
    scraper = TracxnScraper(headless=False)
    
    # SEON company URL
    company_url = "https://tracxn.com/d/companies/seon/__XX9gJBOrnKi_U527Or0hGsnVj2ivM2SwtgE34ahHgMo"
    
    print(f"\nScraping: {company_url}")
    print("-"*70)
    
    # Scrape company data
    result = scraper.scrape_company(company_url)
    
    if result:
        print("\n" + "="*70)
        print("EXTRACTION RESULTS")
        print("="*70)
        
        # Display all extracted fields
        print(f"\n📌 Company Name: {result['company_name']}")
        print(f"📅 Founded Year: {result['founded_year']}")
        print(f"📍 Location: {result['location']}")
        print(f"🏢 Main Office: {result['main_office']}")
        print(f"📮 Registered Address: {result['registered_address']}")
        print(f"💼 Employee Count: {result['employee_count']}")
        
        print(f"\n💰 Funding Information:")
        print(f"   Stage: {result['funding_stage']}")
        print(f"   Total Funding: {result['fundings']['total_funding']}")
        print(f"   Latest Round: {result['fundings']['latest_funding_round']}")
        print(f"   Number of Rounds: {len(result['fundings']['funding_rounds'])}")
        
        if result['fundings']['funding_rounds']:
            print(f"\n   Recent Funding Rounds:")
            for i, round_data in enumerate(result['fundings']['funding_rounds'][:3], 1):
                print(f"      {i}. {round_data.get('round_type', 'N/A')} - "
                      f"{round_data.get('amount', 'N/A')} - "
                      f"{round_data.get('date', 'N/A')}")
        
        # Display investors
        if result['fundings']['investors']:
            print(f"\n   Investors ({len(result['fundings']['investors'])}):")
            for i, investor in enumerate(result['fundings']['investors'][:10], 1):
                print(f"      {i}. {investor}")
        
        print(f"\n🚪 Exit Details: {result['exit_details'] or 'None'}")
        
        # Display acquisitions
        if result['acquisitions']:
            print(f"\n🎯 Acquisitions ({len(result['acquisitions'])}):")
            for acq in result['acquisitions']:
                if isinstance(acq, dict):
                    company = acq.get('company', 'N/A')
                    date = acq.get('date', '')
                    amount = acq.get('amount', '')
                    details = f" - {date}" if date else ""
                    details += f" - {amount}" if amount else ""
                    print(f"   - {company}{details}")
                else:
                    print(f"   - {acq}")
        else:
            print(f"\n🎯 Acquisitions: None")
        
        # Display investments
        if result['investments']:
            print(f"\n💼 Investments Made ({len(result['investments'])}):")
            for inv in result['investments']:
                if isinstance(inv, dict):
                    company = inv.get('company', 'N/A')
                    date = inv.get('date', '')
                    amount = inv.get('amount', '')
                    details = f" - {date}" if date else ""
                    details += f" - {amount}" if amount else ""
                    print(f"   - {company}{details}")
                else:
                    print(f"   - {inv}")
        else:
            print(f"\n💼 Investments Made: None")
        
        print("\n" + "="*70)
        print("✅ SCRAPING SUCCESSFUL!")
        print("="*70)
        
        # Show saved file location
        print(f"\n💾 Data saved to: {scraper.output_file}")
        
        # Pretty print JSON
        print("\n" + "="*70)
        print("JSON OUTPUT:")
        print("="*70)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        return True
    else:
        print("\n" + "="*70)
        print("❌ SCRAPING FAILED")
        print("="*70)
        return False


def test_with_proxy():
    """Test with proxy configuration"""
    print("\n\n" + "="*70)
    print("TESTING WITH PROXY")
    print("="*70)
    
    # Example proxy (replace with your actual proxy)
    proxies = [
        'http://insider_wOhFv:yAu_kjidArup78+@c.oxylabs.io:8000',
    ]
    
    proxy_manager = ProxyManager(proxies)
    scraper = TracxnScraper(proxy_manager=proxy_manager, headless=False)
    
    company_url = "https://tracxn.com/d/companies/seon/__XX9gJBOrnKi_U527Or0hGsnVj2ivM2SwtgE34ahHgMo"
    
    print(f"\nScraping with proxy: {company_url}")
    result = scraper.scrape_company(company_url)
    
    if result:
        print(f"\n✅ Successfully scraped with proxy: {result['company_name']}")
        print(f"💾 Data saved to: {scraper.output_file}")
        return True
    else:
        print("\n❌ Failed to scrape with proxy")
        return False


if __name__ == "__main__":
    # Run test without proxy
    success = test_scraper()
    
    # Uncomment to test with proxy
    # success = test_with_proxy()
    
    sys.exit(0 if success else 1)

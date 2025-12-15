#!/usr/bin/env python3
"""Debug scraper - shows what data is being extracted"""

from scraper import TracxnScraper

print("="*70)
print("DEBUG SCRAPER - SEON Company Test")
print("="*70)

scraper = TracxnScraper(headless=False)
company_url = "https://tracxn.com/d/companies/seon/__XX9gJBOrnKi_U527Or0hGsnVj2ivM2SwtgE34ahHgMo"

print(f"\nScraping: {company_url}\n")

result = scraper.scrape_company(company_url)

if result:
    print("\n" + "="*70)
    print("EXTRACTION RESULTS")
    print("="*70)
    
    for key, value in result.items():
        if key not in ['url', 'scraped_at']:
            print(f"\n{key}: {value}")
else:
    print("\n❌ Scraping failed")

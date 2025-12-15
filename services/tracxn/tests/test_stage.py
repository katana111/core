#!/usr/bin/env python3
"""Быстрый тест Stage extraction"""

from scraper import TracxnScraper

print("Тест извлечения Stage для SEON...")
print("="*60)

scraper = TracxnScraper(headless=True)
url = "https://tracxn.com/d/companies/seon/__XX9gJBOrnKi_U527Or0hGsnVj2ivM2SwtgE34ahHgMo"

result = scraper.scrape_company(url)

if result:
    print(f"\n✅ Результаты:")
    print(f"Company Name: {result['company_name']}")
    print(f"Founded Year: {result['founded_year']}")
    print(f"Location: {result['location']}")
    print(f"Funding Stage: {result['funding_stage']}")
    print(f"Total Funding: {result['fundings']['total_funding']}")
    print(f"Employee Count: {result['employee_count']}")
    print(f"Investors: {len(result['fundings']['investors'])}")
    print(f"Acquisitions: {len(result['acquisitions'])}")
    
    if result['funding_stage']:
        print(f"\n🎉 Stage успешно извлечен: {result['funding_stage']}")
    else:
        print(f"\n⚠️  Stage не извлечен")
else:
    print("\n❌ Ошибка scraping")

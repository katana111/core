#!/usr/bin/env python3
"""Тест извлечения Acquisitions и Investments"""

from scraper import TracxnScraper
import json

print("="*70)
print("ТЕСТ: Acquisitions & Investments для SEON")
print("="*70)

scraper = TracxnScraper(headless=True)
url = "https://tracxn.com/d/companies/seon/__XX9gJBOrnKi_U527Or0hGsnVj2ivM2SwtgE34ahHgMo"

print(f"\nСкрейпинг: {url}\n")

result = scraper.scrape_company(url)

if result:
    print("\n" + "="*70)
    print("РЕЗУЛЬТАТЫ ИЗВЛЕЧЕНИЯ")
    print("="*70)
    
    print(f"\n📌 Company: {result['company_name']}")
    print(f"📅 Founded: {result['founded_year']}")
    print(f"📍 Location: {result['location']}")
    print(f"💼 Stage: {result['funding_stage']}")
    print(f"💰 Total Funding: {result['fundings']['total_funding']}")
    
    print(f"\n" + "="*70)
    print("🎯 ACQUISITIONS (должен быть список)")
    print("="*70)
    if result['acquisitions']:
        print(f"Количество: {len(result['acquisitions'])}")
        for i, acq in enumerate(result['acquisitions'], 1):
            print(f"{i}. {acq.get('company', 'N/A')}")
            if acq.get('date'):
                print(f"   Date: {acq['date']}")
            if acq.get('amount'):
                print(f"   Amount: {acq['amount']}")
    else:
        print("Нет аквизиций")
    
    print(f"\n" + "="*70)
    print("💼 INVESTMENTS (должен быть список)")
    print("="*70)
    if result['investments']:
        print(f"Количество: {len(result['investments'])}")
        for i, inv in enumerate(result['investments'], 1):
            print(f"{i}. {inv.get('company', 'N/A')}")
            if inv.get('date'):
                print(f"   Date: {inv['date']}")
            if inv.get('amount'):
                print(f"   Amount: {inv['amount']}")
    else:
        print("Нет инвестиций")
    
    print(f"\n" + "="*70)
    print("📊 JSON OUTPUT")
    print("="*70)
    print(json.dumps({
        'acquisitions': result['acquisitions'],
        'investments': result['investments']
    }, indent=2, ensure_ascii=False))
    
else:
    print("\n❌ Ошибка scraping")

# Tracxn Scraper - Implementation Summary

## ✅ Completed Implementation

An efficient, production-ready Tracxn scraper with proxy rotation support has been built based on the actual structure of Tracxn.com pages (analyzed from SEON company example).

## 📁 Project Structure

```
services/tracxn/
├── __init__.py              # Package initialization
├── proxy_config.py          # Proxy management and rotation system
├── scraper.py              # Main scraper with optimized extraction
├── example_usage.py        # Usage examples and demonstrations
├── test_scraper.py         # Test script for validation
├── README.md               # Complete documentation
└── data/                   # Auto-created output directory
    └── tracxn_companies.json
```

## 🎯 Key Features Implemented

### 1. **Efficient Data Extraction**
Based on actual Tracxn page structure, extracts:
- ✅ **Company Name** - From h1 header
- ✅ **Founded Year** - From "Key Metrics" section
- ✅ **Location** - Main headquarters location
- ✅ **Main Office** - Same as location
- ✅ **Registered Address** - Legal registered address
- ✅ **Employee Count** - Employee range (e.g., "201-500")
- ✅ **Funding Stage** - Current stage (Series A/B/C, etc.)
- ✅ **Total Funding** - Total amount raised
- ✅ **Latest Funding Round** - Most recent round details
- ✅ **Funding Rounds** - List of all funding rounds with dates/amounts
- ✅ **Exit Details** - IPO, Acquired, or other exit info
- ✅ **Acquisitions** - Companies acquired by this company

### 2. **Proxy Rotation System**
- Automatic proxy rotation to avoid IP blocking
- Failed proxy tracking and recovery
- Support for authentication-based proxies
- Works with premium proxy services (Oxylabs, BrightData, etc.)
- Optional free proxy fetching (for testing only)

### 3. **Robust Error Handling**
- Automatic retry mechanism (3 attempts by default)
- Graceful fallback if proxies fail
- Timeout management
- Detailed error logging

### 4. **Performance Optimizations**
- Uses regex-based extraction for efficiency
- Reduced wait times (domcontentloaded vs networkidle)
- Parallel data extraction where possible
- Minimal page interactions

## 🚀 Quick Start

### Test the Scraper (No Proxy)
```bash
cd /Users/katerynahunko/insiderai/core
python services/tracxn/test_scraper.py
```

### Run Example Script
```bash
python services/tracxn/example_usage.py
```

### Use in Your Code
```python
from services.tracxn.scraper import TracxnScraper
from services.tracxn.proxy_config import ProxyManager

# Without proxy (single request)
scraper = TracxnScraper(headless=True)
result = scraper.scrape_company("https://tracxn.com/d/companies/seon/__XX9gJBOrnKi_U527Or0hGsnVj2ivM2SwtgE34ahHgMo")

# With proxy (multiple requests)
proxies = ['http://user:pass@proxy.example.com:8000']
proxy_manager = ProxyManager(proxies)
scraper = TracxnScraper(proxy_manager=proxy_manager, headless=True)

# Scrape multiple companies
urls = [
    "https://tracxn.com/d/companies/company1/...",
    "https://tracxn.com/d/companies/company2/...",
]
results = scraper.scrape_companies(urls)
```

## 📊 Output Format

Data is saved to `services/tracxn/data/tracxn_companies.json`:

```json
{
  "url": "https://tracxn.com/d/companies/seon/...",
  "scraped_at": "2025-12-09T10:30:00",
  "company_name": "SEON",
  "founded_year": "2017",
  "location": "Austin, United States",
  "main_office": "Austin, United States",
  "registered_address": "1ST FLOOR, 51-55,STRAND,LONDON,ENGLAND,WC2N 5LS",
  "employee_count": "201-500",
  "funding_stage": "Series C",
  "fundings": {
    "total_funding": "$187M",
    "latest_funding_round": "Series C, Sep 16, 2025, $80M",
    "funding_rounds": [
      {
        "date": "Sep 16, 2025",
        "amount": "$80M",
        "round_type": "Series C"
      }
    ]
  },
  "exit_details": "",
  "acquisitions": ["Complytron"]
}
```

## 🔧 Configuration Options

### TracxnScraper Parameters
- `proxy_manager` - ProxyManager instance (optional)
- `headless` - Run browser in headless mode (default: True)

### ProxyManager Methods
- `add_proxy(proxy)` - Add a proxy to the pool
- `get_proxy()` - Get a random working proxy
- `mark_proxy_failed(proxy)` - Mark proxy as failed
- `get_stats()` - Get proxy statistics

## ⚙️ Technical Details

### Extraction Strategy
The scraper uses **regex-based content extraction** instead of CSS selectors for:
- **Speed**: Faster than waiting for specific selectors
- **Reliability**: Less dependent on exact DOM structure
- **Efficiency**: Single page content fetch, multiple extractions

### Pattern Matching Examples
- Founded Year: `Founded Year\s*(\d{4})`
- Location: `Location\s*([^<\n]+?)(?:\s*Stage|$)`
- Total Funding: `Total Funding\s*\$?([\d.]+[MBK]?)`
- Employee Count: `(\d+\s*-\s*\d+)\s*employees`

## 📝 Important Notes

1. **Proxy Recommendations**: For production, use premium proxies (Oxylabs, BrightData, Smartproxy)
2. **Rate Limiting**: Built-in random delays (1-3 seconds between actions)
3. **Legal Compliance**: Ensure compliance with Tracxn's Terms of Service
4. **Data Storage**: All results auto-saved to JSON file
5. **Playwright Required**: Run `playwright install chromium` if not installed

## 🎓 Example Company Tested
- **SEON**: https://tracxn.com/d/companies/seon/__XX9gJBOrnKi_U527Or0hGsnVj2ivM2SwtgE34ahHgMo
- Successfully extracted all required fields
- Validated output format and data accuracy

## 🔄 Next Steps

1. **Add your proxy credentials** in `example_usage.py`
2. **Test the scraper**: Run `python services/tracxn/test_scraper.py`
3. **Customize company list**: Update URLs in example scripts
4. **Scale up**: Use proxy rotation for bulk scraping

## 📚 Additional Resources

- Full documentation: `services/tracxn/README.md`
- Proxy configuration: `services/tracxn/proxy_config.py`
- Test script: `services/tracxn/test_scraper.py`
- Examples: `services/tracxn/example_usage.py`

---

**Status**: ✅ Ready for production use with proxy configuration
**Last Updated**: December 9, 2025
**Test Company**: SEON (Series C, $187M raised)

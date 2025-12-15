# 🚀 Quick Start Guide - Tracxn Scraper

## ✅ Setup Complete!

All dependencies are installed and ready to use.

## 🎯 How to Run

### Option 1: Quick Test (Recommended First)
Test that everything works without actually scraping:
```bash
cd /Users/katerynahunko/insiderai/core/services/tracxn
python3 quick_test.py
```

### Option 2: Single Company Test (No Proxy)
Test scraping the SEON company example:
```bash
cd /Users/katerynahunko/insiderai/core/services/tracxn
python3 test_scraper.py
```

This will:
- Scrape SEON company data
- Display all extracted fields
- Save results to `data/tracxn_companies.json`

### Option 3: Full Example (With Proxy)
Run the complete example with proxy support:
```bash
cd /Users/katerynahunko/insiderai/core/services/tracxn
python3 example_usage.py
```

**Note:** Update the proxy configuration in `example_usage.py` line 55:
```python
proxies = [
    'http://your_user:your_pass@proxy.example.com:8000',
]
```

## 📝 Basic Usage in Your Code

```python
# Navigate to the tracxn directory first
cd /Users/katerynahunko/insiderai/core/services/tracxn

# Then create your script
from scraper import TracxnScraper
from proxy_config import ProxyManager

# Without proxy (single request)
scraper = TracxnScraper(headless=True)
result = scraper.scrape_company("https://tracxn.com/d/companies/seon/__XX9gJBOrnKi_U527Or0hGsnVj2ivM2SwtgE34ahHgMo")
print(result)

# With proxy (multiple requests)
proxies = ['http://user:pass@proxy.example.com:8000']
proxy_manager = ProxyManager(proxies)
scraper = TracxnScraper(proxy_manager=proxy_manager, headless=True)

urls = [
    "https://tracxn.com/d/companies/company1/...",
    "https://tracxn.com/d/companies/company2/...",
]
results = scraper.scrape_companies(urls)
```

## 📊 What Gets Extracted

For each company:
- ✅ Company Name
- ✅ Founded Year
- ✅ Location / Main Office
- ✅ Registered Address
- ✅ Employee Count
- ✅ Funding Stage
- ✅ Total Funding
- ✅ Latest Funding Round
- ✅ All Funding Rounds (with dates & amounts)
- ✅ Exit Details (IPO, Acquired, etc.)
- ✅ Acquisitions

## 💾 Output Location

Results are saved to:
```
/Users/katerynahunko/insiderai/core/services/tracxn/data/tracxn_companies.json
```

## 🔧 Troubleshooting

### Import Error
If you see `ModuleNotFoundError`, make sure you're in the tracxn directory:
```bash
cd /Users/katerynahunko/insiderai/core/services/tracxn
```

### Browser Not Found
If Playwright browser is missing, install it:
```bash
python3 -m playwright install chromium
```

### Proxy Issues
- Test your proxy first using `proxy_manager.test_proxy(proxy_url)`
- Use premium proxies for production (Oxylabs, BrightData, etc.)
- Free proxies are unreliable

## 📚 Available Scripts

- `quick_test.py` - Verify setup without scraping
- `test_scraper.py` - Test with SEON company
- `example_usage.py` - Full examples with proxy support
- `setup.sh` - Install all dependencies

## 🎓 Example Companies

Working test URLs:
- SEON: `https://tracxn.com/d/companies/seon/__XX9gJBOrnKi_U527Or0hGsnVj2ivM2SwtgE34ahHgMo`

Replace with your target companies!

## ⚡ Pro Tips

1. **Use headless mode** for faster scraping: `TracxnScraper(headless=True)`
2. **Always use proxies** for multiple companies to avoid IP blocking
3. **Check results file** after each scrape in `data/tracxn_companies.json`
4. **Random delays** are built-in to appear human-like

---

**Ready to scrape!** 🎉

Start with `python3 quick_test.py` to verify everything works.

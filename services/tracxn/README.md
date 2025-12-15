# Tracxn Scraper Service

Scrapes company data from Tracxn.com with proxy rotation and automatic database integration.

## Features

✅ **Company Data Extraction** - Funding, employees, location, stage, etc.  
✅ **Proxy Rotation** - Avoid blocking with automatic proxy switching  
✅ **Database Integration** - Auto-save to MySQL `competitors` table  
✅ **Acquisitions & Investments** - Extract company acquisition and investment data  
✅ **JSON Export** - Save results to `data/tracxn_companies.json`  

## Quick Start

```bash
# Install dependencies
bash setup.sh

# Run example
PYTHONPATH=/Users/katerynahunko/insiderai/core python3 example_usage.py
```

## Usage

### Basic Scraping with Database

```python
from database import get_db
from scraper import TracxnScraper

# Initialize database
db = get_db()
db.initialize()

# Create scraper with auto DB saving
scraper = TracxnScraper(save_to_db=True)

# Scrape company (auto-saves to database)
url = "https://tracxn.com/d/companies/seon/..."
result = scraper.scrape_company(url)
```

### With Proxy Support

```python
from proxy_config import ProxyManager

proxies = ['http://user:pass@proxy.com:8000']
proxy_manager = ProxyManager(proxies)

scraper = TracxnScraper(proxy_manager=proxy_manager, save_to_db=True)
results = scraper.scrape_companies([url1, url2, url3])
```

## Project Structure

```
tracxn/
├── scraper.py              # Main scraper class
├── proxy_config.py         # Proxy management
├── db_operations.py        # Database operations
├── example_usage.py        # Usage examples
├── data/                   # JSON output
├── tests/                  # Test scripts
└── docs/                   # Documentation
```

## Configuration

Set database credentials in `.env`:

```bash
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=insider
DB_USERNAME=root
DB_PASSWORD=password
```

## Testing

```bash
cd tests/
PYTHONPATH=/Users/katerynahunko/insiderai/core python3 test_scraper.py
```

## Documentation

- `/database/README.md` - Database integration
- `docs/IMPLEMENTATION.md` - Technical details
- `docs/QUICKSTART.md` - Getting started

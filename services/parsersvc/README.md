# Parsers.vc Scraper Service

A service to scrape company data from parsers.vc and enrich competitor records in the database.

## Features

- **Single Company Scraping**: Scrape individual company data from parsers.vc
- **Batch Processing**: Automatically enrich all competitors in database
- **Smart Funding Comparison**: Compares total raised amounts and keeps the higher value
- **Database Integration**: Uses centralized database package for connection management
- **Retry Logic**: Automatic retries on failure (up to 3 attempts)
- **Rate Limiting**: Configurable delay between requests

## Data Extracted

The scraper extracts the following fields from parsers.vc:

- **Location**: Company headquarters/location
- **Employees**: Employee count (supports ranges like "50-100")
- **Total Raised**: Total funding raised (automatically compares with existing data)
- **Founded Year**: Year the company was founded
- **Categories**: Company categories/tags (e.g., AI, Fintech, SaaS)
- **Press Mentions**: Media coverage and press articles (with AI-powered analysis)

## Database Mapping

### Competitors Table

Parsers.vc data is mapped to the `competitors` table:

| Parsers.vc Field | Database Field | Notes |
|-----------------|----------------|-------|
| Location | `address` | Company location/headquarters |
| Employees | `employee_qty` | Midpoint of range if "50-100" format |
| Total Raised | `fundings_total` | Compares with existing, keeps higher value |
| Founded Year | `founded_year` | 4-digit year |
| Categories | `categories` | JSON array of category tags |

### Competitors News Table (NEW)

Press mentions are analyzed with AI and saved to `competitors_news`:

| Field | Type | Description |
|-------|------|-------------|
| competitor_id | Foreign Key | Links to competitors table |
| title | Text | Article title/headline |
| content | Text | Article excerpt |
| published_date | Date | Publication date |
| **summary** | Text | AI-generated summary |
| **sentiment** | Enum | positive/negative/neutral/mixed |
| **sentiment_score** | Decimal | -1.0 to 1.0 |
| **key_topics** | JSON | AI-identified topics |
| **analysis** | Text | Business impact analysis |

See [AI News Analyzer Setup](../ai/README.md) for configuration details.

## Installation

Ensure Playwright is installed:

```bash
pip install playwright
playwright install chromium
```

## Usage

### Single Company Scraping

```python
from services.parsersvc.scraper import ParsersVCScraper

scraper = ParsersVCScraper(headless=True)
data = scraper.scrape_company("seon.io")

print(data)
# {
#   'website': 'seon.io',
#   'location': 'Budapest, Hungary',
#   'employees': '50-100',
#   'total_raised': 94000000.0,
#   'founded_year': '2017',
#   'scraped_at': '2024-01-15T10:30:00'
# }
```

### Save to Database

```python
from database import get_db
from services.parsersvc.scraper import ParsersVCScraper
from services.parsersvc.db_operations import ParsersVCDataOperations

# Initialize
db = get_db()
db.initialize()

scraper = ParsersVCScraper(headless=True)
db_ops = ParsersVCDataOperations()

# Scrape and save
data = scraper.scrape_company("seon.io")
if data:
    success = db_ops.save_competitor(data)
```

### Batch Enrichment

```python
from database import get_db
from services.parsersvc.enrichment_service import CompetitorEnrichmentService

# Initialize database
db = get_db()
db.initialize()

# Create service
service = CompetitorEnrichmentService(
    headless=True,
    delay_between_requests=2.0  # 2 seconds between requests
)

# Enrich all competitors
results = service.enrich_all_competitors(limit=None)

print(f"Processed: {results['processed']}")
print(f"Successful: {results['successful']}")
print(f"Failed: {results['failed']}")
```

### Limit Batch Processing

```python
# Process only first 10 competitors
results = service.enrich_all_competitors(limit=10)
```

## Architecture

### Components

1. **ParsersVCScraper** (`scraper.py`)
   - Handles web scraping with Playwright
   - Extracts company data using regex patterns
   - Converts funding amounts to numeric values
   - Retry logic for failed requests

2. **ParsersVCDataOperations** (`db_operations.py`)
   - Database operations for parsers.vc data
   - Maps scraped data to competitors table
   - Compares funding amounts (keeps higher value)
   - Updates existing competitor records

3. **CompetitorEnrichmentService** (`enrichment_service.py`)
   - Batch processing service
   - Loops through all competitors in database
   - Cleans website URLs (removes http/https)
   - Provides progress tracking and statistics

## Data Comparison Logic

The service implements smart data comparison:

### Funding Amount Comparison

When both parsers.vc and existing database have funding data:
- Compares both values
- Keeps the **higher** amount
- Logs the comparison for transparency

Example:
```
Funding comparison - New: $94,000,000, Existing: $187,000,000, Keeping: $187,000,000
```

### Employee Range Handling

Employee counts in range format (e.g., "50-100"):
- Takes the midpoint: (50 + 100) / 2 = 75
- Stores as integer in `employee_qty`

## Configuration

### Environment Variables

Uses centralized database configuration from `/database/`:

```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=insider
DB_USERNAME=root
DB_PASSWORD=password
```

### Scraper Settings

```python
scraper = ParsersVCScraper(
    headless=True  # Run browser in headless mode
)
```

### Enrichment Settings

```python
service = CompetitorEnrichmentService(
    headless=True,                 # Browser mode
    delay_between_requests=2.0     # Delay in seconds
)
```

## Error Handling

- **Retry Logic**: Up to 3 attempts per company
- **Validation**: Checks for valid website before scraping
- **Graceful Failures**: Logs errors and continues with next competitor
- **Statistics Tracking**: Reports success/failure counts

## Examples

Run the example script:

```bash
cd /Users/katerynahunko/insiderai/core
export PYTHONPATH=/Users/katerynahunko/insiderai/core
python services/parsersvc/example_usage.py
```

This will demonstrate:
1. Single company scraping
2. Saving to database
3. Batch enrichment (first 5 competitors)

## Notes

- The service only **updates** existing competitors, it doesn't create new ones
- Website URLs are automatically cleaned (removes http://, https://, www.)
- Designed to work alongside Tracxn scraper for comprehensive data enrichment
- Uses the centralized `/database/` package for connection management

## Integration with Tracxn Service

Both services update the same `competitors` table:

| Field | Tracxn | Parsers.vc |
|-------|--------|------------|
| name | ✓ | - |
| website | ✓ | - |
| address | ✓ | ✓ |
| email | ✓ | - |
| pricing | ✓ | - |
| founded_year | ✓ | ✓ |
| funding_stage | ✓ | - |
| fundings_total | ✓ | ✓ (compared) |
| employee_qty | ✓ | ✓ |
| founders | ✓ | - |

This allows you to:
1. Use Tracxn to create initial competitor records
2. Use Parsers.vc to enrich/update location and funding data
3. Compare funding amounts from multiple sources

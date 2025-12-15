# BiometricUpdate News Enrichment Service

This service searches for company news articles on [biometricupdate.com](https://www.biometricupdate.com/) and enriches the `competitors_news` table with AI-analyzed content.

## Overview

The BiometricUpdate service consists of three main components:

1. **Scraper** (`scraper.py`) - Searches and extracts article content from biometricupdate.com
2. **Database Operations** (`db_operations.py`) - Saves articles with AI analysis to competitors_news table
3. **Enrichment Service** (`enrichment_service.py`) - Batch processes all competitors

## Features

- 🔍 **Google Site Search**: Uses Google to find relevant articles on biometricupdate.com
- 📰 **Content Extraction**: Extracts article titles, content, dates, and URLs
- 🧠 **AI Analysis**: Analyzes articles with Meta Llama 3.2 3B model via OpenRouter
- 📊 **Sentiment Analysis**: Determines sentiment and importance grade (1-10)
- 🗄️ **Database Integration**: Saves to existing competitors_news table structure
- ⚡ **Rate Limiting**: Respectful scraping with built-in delays
- 🔄 **Duplicate Detection**: Prevents saving the same article twice
- 📈 **Batch Processing**: Process all competitors at once with progress tracking
- 🔒 **Biometric Focus**: Specialized content filtering for biometric/security industry news

## Quick Start

### Run Enrichment for All Competitors

```python
import asyncio
from services.biometricupdate.enrichment_service import enrich_competitors_with_biometricupdate

async def main():
    # Enrich all competitors with AI analysis
    results = await enrich_competitors_with_biometricupdate()
    print(f"Processed {results['companies_processed']} companies")
    print(f"Saved {results['total_articles_saved']} articles")

asyncio.run(main())
```

### Run for Specific Companies

```python
# Enrich only specific companies
companies = ["Seon", "LexisNexis", "Trusting Social"]
results = await enrich_competitors_with_biometricupdate(competitor_names=companies)
```

### Run Without AI Analysis (Faster)

```python
# Skip AI analysis for faster processing
results = await enrich_competitors_with_biometricupdate(analyze_news=False)
```

## Usage Examples

Run the example file to see all usage patterns:

```bash
cd /Users/katerynahunko/insiderai/core
PYTHONPATH=/Users/katerynahunko/insiderai/core python3 services/biometricupdate/example_usage.py
```

## Component Details

### Scraper (`scraper.py`)

```python
from services.biometricupdate.scraper import BiometricUpdateScraper

scraper = BiometricUpdateScraper()
articles = await scraper.scrape_company_news("Seon", max_articles=10)
```

**Features:**
- Google site search integration (`site:biometricupdate.com "company name"`)
- Multiple content extraction strategies
- Date parsing from various HTML patterns
- Biometric-focused content filtering (extracts relevant sentences about biometrics, identity, security)
- Rate limiting and retry logic

### Database Operations (`db_operations.py`)

```python
from services.biometricupdate.db_operations import BiometricUpdateDataOperations

db_ops = BiometricUpdateDataOperations(analyze_news=True)
result = db_ops.save_company_articles("Seon", articles)
```

**Features:**
- AI analysis integration with fallback
- Duplicate detection by title and URL
- Flexible company name matching
- Structured data mapping to competitors_news table

### Enrichment Service (`enrichment_service.py`)

```python
from services.biometricupdate.enrichment_service import BiometricUpdateEnrichmentService

service = BiometricUpdateEnrichmentService(analyze_news=True)
results = await service.enrich_all_competitors()
```

**Features:**
- Batch processing with progress tracking
- Comprehensive statistics and reporting
- Error handling and recovery
- Rate limiting between companies

## Database Schema

Articles are saved to the existing `competitors_news` table:

```sql
CREATE TABLE competitors_news (
    id INT PRIMARY KEY AUTO_INCREMENT,
    competitor_id INT,
    title VARCHAR(255),
    date DATE,
    link TEXT,
    analysis TEXT,
    importance_grade INT,
    sentiment VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## AI Analysis

Uses OpenRouter API with Meta Llama 3.2 3B Instruct model:

- **Title Cleaning**: Extracts first sentence if title is too long
- **Main Ideas**: Generates 2-3 sentence summary of key points
- **Sentiment Analysis**: Positive/negative/neutral with confidence score
- **Importance Grading**: 1-10 scale based on sentiment strength
- **Fallback Mode**: Rule-based analysis when API unavailable
- **Biometric Context**: Specialized analysis for biometric/security industry content

## Configuration

The service uses existing infrastructure:

- **Database**: Centralized database connection from `/database/`
- **AI Analyzer**: Shared news analyzer from `/services/ai/news_analyzer.py`
- **Environment**: Requires PYTHONPATH set to project root

## Rate Limiting

- **Between searches**: 2-4 seconds delay
- **Between articles**: 1-2 seconds delay
- **Between companies**: 2 seconds delay
- **Retry logic**: 3 attempts with exponential backoff

## Error Handling

- **Missing companies**: Logs warning and continues
- **Scraping failures**: Retries up to 3 times
- **AI analysis errors**: Falls back to rule-based analysis
- **Database errors**: Logs error and continues with next article
- **Network timeouts**: Implements timeout and retry logic

## Biometric Industry Focus

Specialized for biometric and security industry news:

- **Keyword Focus**: biometric, authentication, identity, security, fraud, verification, facial, fingerprint, iris, voice
- **Content Filtering**: Extracts sentences most relevant to biometric technologies
- **Company Context**: Prioritizes content that mentions target companies in biometric contexts
- **Industry Relevance**: Filters for articles relevant to identity verification and fraud prevention

## Output Example

```
🔍 Searching for articles about 'Seon'...
  📰 Found 7 articles
  ✅ Saved 5/7 articles
     (Skipped 2 duplicates)

📊 Final Statistics:
   Companies processed: 6
   Success rate: 100.0%
   Total articles saved: 28
```

## Integration with Existing Services

This service complements the existing news sources:

- **ParsersVC**: Extracts press mentions from parsers.vc competitor profiles
- **SolutionsReview**: Searches for general tech industry articles
- **BiometricUpdate**: Searches for biometric/security industry specific news
- **Shared Infrastructure**: All use the same AI analyzer and database structure

Together, they provide comprehensive competitor intelligence from multiple industry-specific sources.

## Dependencies

- `playwright` - Browser automation for web scraping
- `dateutil` - Date parsing
- `requests` - HTTP requests for search
- Centralized database package
- Shared AI news analyzer

## Troubleshooting

### No articles found
- Check if company name exists in competitors table
- Verify internet connection for Google search
- Company might not have recent coverage on biometricupdate.com
- Try alternative company name variations

### AI analysis failing
- Check OpenRouter API key in environment
- Service automatically falls back to rule-based analysis
- Verify API rate limits not exceeded

### Database connection errors
- Ensure MySQL server is running (127.0.0.1:3306)
- Check database credentials
- Verify competitors table exists

### Rate limiting
- Service includes built-in rate limiting
- Increase delays in scraper if needed
- Check for IP blocking (rare)

## Support

For issues or questions:
1. Check the example usage file
2. Review error logs for specific error messages
3. Verify all dependencies are installed
4. Ensure PYTHONPATH is correctly set
5. Test with individual companies first before batch processing
# GlobeNewswire News Enrichment Service

This service scrapes competitor news articles from [GlobeNewswire](https://www.globenewswire.com/), a leading press release distribution platform. It provides comprehensive tools for discovering, analyzing, and storing business-relevant news about your competitors.

## 🌟 Features

- **🔍 Advanced Search**: Searches GlobeNewswire using company names to find relevant press releases and news articles
- **🤖 AI-Powered Analysis**: Uses AI to analyze articles for sentiment, key topics, and business impact
- **📊 Smart Filtering**: Automatically filters content to focus on business-relevant news (goals, successes, releases, contracts, etc.)
- **💾 Database Integration**: Seamlessly saves enriched data to MySQL database with duplicate detection
- **🚀 Async Processing**: Built with async/await for efficient concurrent operations
- **📈 Business Focus**: Optimized for press releases about company announcements, partnerships, acquisitions, and product launches

## 📋 Prerequisites

- Python 3.12+
- MySQL database with competitors and competitors_news tables
- Playwright for web scraping: `pip install playwright && playwright install chromium`
- Optional: OpenRouter API key for enhanced AI analysis

## 🚀 Quick Start

### Basic Usage

```python
import asyncio
from services.globenewswire import enrich_competitors_with_globenewswire

# Enrich a single competitor
async def main():
    result = await enrich_competitors_with_globenewswire(
        competitor_names=['Seon'],
        analyze_news=True,
        max_articles_per_company=5
    )
    print(f"Found and saved {result['total_articles_saved']} articles")

asyncio.run(main())
```

### Service Class Usage

```python
from services.globenewswire import GlobeNewswireEnrichmentService

# Initialize service
service = GlobeNewswireEnrichmentService(
    analyze_news=True,
    max_articles_per_company=10
)

# Enrich specific competitors
result = await service.enrich_specific_competitors(['Seon', 'LexisNexis'])

# Get statistics
stats = service.get_statistics()
print(f"Total articles in database: {stats['total_articles']}")
```

## 🏗️ Architecture

### Core Components

1. **GlobeNewswireScraper** (`scraper.py`)
   - Handles web scraping from GlobeNewswire search results
   - Extracts article content, titles, dates, and metadata
   - Built with Playwright for robust browser automation

2. **GlobeNewswireDataOperations** (`db_operations.py`)
   - Manages database operations and AI analysis integration
   - Handles article deduplication and relevance filtering
   - Provides statistics and recent article retrieval

3. **GlobeNewswireEnrichmentService** (`enrichment_service.py`)
   - Orchestrates complete enrichment workflows
   - Coordinates scraping, analysis, and database operations
   - Provides batch processing capabilities

### Data Flow

```
Company Names → Search GlobeNewswire → Extract Articles → AI Analysis → Database Storage
```

## 🔧 Configuration

### Environment Variables

```bash
# Optional: For enhanced AI analysis
export OPENROUTER_API_KEY="your_openrouter_api_key"

# Database connection (handled by database package)
export MYSQL_HOST="localhost"
export MYSQL_USER="your_username"  
export MYSQL_PASSWORD="your_password"
export MYSQL_DATABASE="insider"
```

### Scraper Settings

```python
# Customize scraper behavior
scraper = GlobeNewswireScraper(
    headless=True,  # Run browser in background
    delay_between_requests=2.0  # Respectful rate limiting
)
```

## 📊 Database Schema

Articles are saved to the `competitors_news` table with the following fields:

```sql
- competitor_id: Links to competitors table
- title: Article headline
- url: Original article URL
- content: Full article text
- published_date: When article was published
- source: Always 'globenewswire'
- summary: AI-generated summary (if AI analysis enabled)
- sentiment: positive/negative/neutral
- key_topics: Comma-separated topics
- business_impact: AI assessment of business relevance
- confidence_score: AI confidence in analysis
- created_at: When record was saved
```

## 🎯 Use Cases

### 1. Competitor Intelligence
Monitor press releases and announcements from key competitors to stay informed about their business developments.

### 2. Market Research
Analyze sentiment and topics across industry news to identify trends and opportunities.

### 3. Partnership Opportunities
Discover potential collaboration opportunities through company announcements and partnerships.

### 4. Investment Research
Track funding announcements, acquisitions, and other financial news about companies.

## 📈 Performance & Limitations

### Performance
- **Scraping Speed**: ~2-3 seconds per article (respectful rate limiting)
- **AI Analysis**: ~1-2 seconds per article when enabled
- **Concurrent Processing**: Async design allows efficient batch operations
- **Memory Usage**: Optimized for processing large batches

### GlobeNewswire Specific Notes
- **Content Quality**: High-quality press releases with structured format
- **Search Accuracy**: Good company name matching and relevance
- **Update Frequency**: Real-time press release distribution
- **Coverage**: Global press releases across all industries

### Limitations
- Requires company names to be reasonably accurate for search
- Rate limited to be respectful to GlobeNewswire servers
- AI analysis quality depends on article content clarity
- Some articles may be duplicates across different search terms

## 🔍 Examples

See `example_usage.py` for comprehensive examples including:

- Basic article scraping
- Full enrichment with AI analysis
- Multi-company batch processing
- Database operations and statistics
- Error handling patterns
- Fast mode without AI analysis

## 🛠️ Troubleshooting

### Common Issues

1. **No Articles Found**
   - Verify company name spelling and format
   - Check if company has recent press releases on GlobeNewswire
   - Try variations of company name (with/without "Inc", "Ltd", etc.)

2. **Scraping Errors**
   - Ensure stable internet connection
   - Check if GlobeNewswire website structure has changed
   - Verify Playwright and Chromium are properly installed

3. **Database Errors**
   - Confirm database connection and table schema
   - Check that competitor exists in competitors table
   - Verify MySQL permissions for insert operations

4. **AI Analysis Issues**
   - OpenRouter API key may be missing or invalid
   - Service falls back to rule-based analysis automatically
   - Check API rate limits and usage quotas

### Debug Mode

```python
# Enable debug output
scraper = GlobeNewswireScraper(headless=False)  # See browser actions
```

## 🔗 Integration

### With Unified Service

This service integrates seamlessly with the unified enrichment service:

```python
from services.unified_enrichment import enrich_all_competitors_unified

# Include GlobeNewswire in unified processing
result = await enrich_all_competitors_unified(
    competitor_names=['Seon'],
    sources=['globenewswire', 'biometricupdate', 'solutionsreview'],
    analyze_news=True
)
```

### With Other Services

Combine with other news sources for comprehensive competitor intelligence:

```python
# Use alongside other enrichment services
from services.biometricupdate import enrich_competitors_with_biometricupdate
from services.solutionsreview import enrich_competitors_with_solutionsreview

# Run in parallel for faster processing
results = await asyncio.gather(
    enrich_competitors_with_globenewswire(['Seon']),
    enrich_competitors_with_biometricupdate(['Seon']),
    enrich_competitors_with_solutionsreview(['Seon'])
)
```

## 📝 Recent Updates

- **v1.0.0**: Initial implementation with full scraping and AI analysis
- Integrated business relevance filtering
- Added comprehensive error handling and logging
- Optimized for GlobeNewswire's press release format
- Added support for unified service orchestration

## 🤝 Contributing

When extending this service:

1. Maintain the async/await pattern for scalability
2. Follow the established error handling conventions
3. Add comprehensive logging for debugging
4. Update tests when modifying scraping logic
5. Document any new configuration options

## 🔒 Privacy & Ethics

- Respects robots.txt and implements reasonable rate limiting
- Only scrapes publicly available press releases
- No personal data collection
- AI analysis is performed on publicly available business content only
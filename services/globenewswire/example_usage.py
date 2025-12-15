"""
Example usage of GlobeNewswire enrichment service.
Demonstrates various ways to use the GlobeNewswire scraper and enrichment tools.
"""

import asyncio
from services.globenewswire.scraper import GlobeNewswireScraper
from services.globenewswire.db_operations import GlobeNewswireDataOperations
from services.globenewswire.enrichment_service import enrich_competitors_with_globenewswire


async def example_1_basic_scraping():
    """Example 1: Basic scraping for a single company"""
    print("\\n" + "="*60)
    print("EXAMPLE 1: Basic Scraping")
    print("="*60)
    
    async with GlobeNewswireScraper(headless=True) as scraper:
        articles = await scraper.search_company_news("Seon", max_articles=3)
        
        print(f"Found {len(articles)} articles:")
        for i, article in enumerate(articles, 1):
            print(f"\\n{i}. {article['title']}")
            print(f"   URL: {article['url']}")
            print(f"   Date: {article['published_date']}")
            print(f"   Content: {article['content'][:100]}...")


async def example_2_full_enrichment_single_company():
    """Example 2: Full enrichment (scraping + AI analysis + database save) for single company"""
    print("\\n" + "="*60)
    print("EXAMPLE 2: Full Enrichment - Single Company")
    print("="*60)
    
    result = await enrich_competitors_with_globenewswire(
        competitor_names=['Seon'],
        analyze_news=True,
        max_articles_per_company=5
    )
    
    print(f"Enrichment Results:")
    print(f"- Status: {result['status']}")
    print(f"- Companies processed: {result['companies_processed']}")
    print(f"- Articles found: {result['total_articles_found']}")
    print(f"- Articles saved: {result['total_articles_saved']}")
    print(f"- Success rate: {result['success_rate']:.1f}%")
    print(f"- Processing time: {result['processing_time_seconds']:.2f} seconds")


async def example_3_multiple_companies():
    """Example 3: Enrich multiple companies at once"""
    print("\\n" + "="*60)
    print("EXAMPLE 3: Multiple Companies Enrichment")
    print("="*60)
    
    companies = ['Seon', 'LexisNexis', 'Mastercard']
    
    result = await enrich_competitors_with_globenewswire(
        competitor_names=companies,
        analyze_news=True,
        max_articles_per_company=3
    )
    
    print(f"Multi-company Results:")
    print(f"- Companies targeted: {len(companies)}")
    print(f"- Companies processed: {result['companies_processed']}")
    print(f"- Total articles found: {result['total_articles_found']}")
    print(f"- Total articles saved: {result['total_articles_saved']}")
    print(f"- Overall success rate: {result['success_rate']:.1f}%")


def example_4_database_operations():
    """Example 4: Database operations and statistics"""
    print("\\n" + "="*60)
    print("EXAMPLE 4: Database Operations")
    print("="*60)
    
    db_ops = GlobeNewswireDataOperations(analyze_news=False)
    
    # Get all competitors
    competitors = db_ops.get_all_competitors()
    print(f"Total competitors in database: {len(competitors)}")
    
    # Get statistics
    stats = db_ops.get_save_statistics()
    print(f"\\nGlobeNewswire Statistics:")
    print(f"- Total articles: {stats['total_articles']}")
    print(f"- Companies covered: {stats['companies_covered']}")
    print(f"- Average confidence: {stats['avg_confidence']}")
    print(f"- Positive articles: {stats['positive_articles']}")
    print(f"- Negative articles: {stats['negative_articles']}")
    print(f"- Neutral articles: {stats['neutral_articles']}")
    
    # Get recent articles for Seon
    recent_articles = db_ops.get_recent_news('Seon', days=30, limit=5)
    print(f"\\nRecent Seon articles ({len(recent_articles)}):")
    for i, article in enumerate(recent_articles, 1):
        print(f"{i}. {article['title']}")
        print(f"   Date: {article['published_date']}")
        print(f"   Sentiment: {article['sentiment']}")


async def example_5_without_ai_analysis():
    """Example 5: Fast enrichment without AI analysis"""
    print("\\n" + "="*60)
    print("EXAMPLE 5: Fast Mode (No AI Analysis)")
    print("="*60)
    
    result = await enrich_competitors_with_globenewswire(
        competitor_names=['Seon'],
        analyze_news=False,  # Skip AI analysis for speed
        max_articles_per_company=5
    )
    
    print(f"Fast Mode Results:")
    print(f"- Articles found: {result['total_articles_found']}")
    print(f"- Articles saved: {result['total_articles_saved']}")
    print(f"- Processing time: {result['processing_time_seconds']:.2f} seconds")
    print(f"- AI analysis: Disabled (faster processing)")


async def example_6_error_handling():
    """Example 6: Error handling for non-existent companies"""
    print("\\n" + "="*60)
    print("EXAMPLE 6: Error Handling")
    print("="*60)
    
    # Try to enrich a company that doesn't exist in our database
    result = await enrich_competitors_with_globenewswire(
        competitor_names=['NonExistentCompany123'],
        analyze_news=True,
        max_articles_per_company=3
    )
    
    print(f"Error Handling Results:")
    print(f"- Status: {result['status']}")
    print(f"- Message: {result['message']}")
    print(f"- Companies processed: {result['companies_processed']}")
    print(f"- Errors: {len(result.get('errors', []))}")


async def main():
    """Run all examples"""
    print("🌐 GlobeNewswire Service Examples")
    print("This demonstrates various ways to use the GlobeNewswire enrichment service.")
    print("\\nNote: These examples will make real requests to GlobeNewswire.")
    print("Processing may take several minutes depending on network speed.")
    
    try:
        # Example 1: Basic scraping
        await example_1_basic_scraping()
        
        # Example 2: Full enrichment for single company  
        await example_2_full_enrichment_single_company()
        
        # Example 3: Multiple companies
        # await example_3_multiple_companies()  # Commented to save time
        
        # Example 4: Database operations
        example_4_database_operations()
        
        # Example 5: Without AI analysis
        await example_5_without_ai_analysis()
        
        # Example 6: Error handling
        await example_6_error_handling()
        
        print("\\n🎉 All examples completed successfully!")
        
    except Exception as e:
        print(f"\\n❌ Error running examples: {e}")


if __name__ == "__main__":
    # Set up environment
    import os
    import sys
    
    # Add the project root to Python path
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # Run examples
    asyncio.run(main())
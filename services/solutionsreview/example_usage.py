"""
Example usage of SolutionsReview enrichment service
Demonstrates how to scrape and analyze company news from solutionsreview.com
"""

import asyncio
from services.solutionsreview.enrichment_service import enrich_competitors_with_solutionsreview
from services.solutionsreview.scraper import SolutionsReviewScraper
from services.solutionsreview.db_operations import SolutionsReviewDataOperations


async def example_1_enrich_all_competitors():
    """Example 1: Enrich all competitors from database with SolutionsReview articles"""
    
    print("🚀 Example 1: Enriching all competitors with SolutionsReview articles")
    print("=" * 80)
    
    # Run enrichment for all competitors in database with AI analysis
    results = await enrich_competitors_with_solutionsreview(analyze_news=True)
    
    # Print detailed results
    if results.get('status') == 'completed':
        print(f"\n📊 Final Statistics:")
        print(f"   Companies processed: {results['companies_processed']}")
        print(f"   Success rate: {results['success_rate']:.1f}%")
        print(f"   Total articles saved: {results['total_articles_saved']}")
        
        # Show per-company results
        if 'results' in results:
            print(f"\n📋 Per-Company Results:")
            for result in results['results']:
                status_emoji = {"success": "✅", "error": "❌", "no_articles": "⚠️"}.get(result['status'], "❓")
                print(f"   {status_emoji} {result['company']}: {result.get('articles_saved', 0)} articles saved")


async def example_2_specific_companies():
    """Example 2: Enrich specific companies only"""
    
    print("\n🚀 Example 2: Enriching specific companies")
    print("=" * 80)
    
    # List of specific companies to enrich
    companies = ["Palantir", "Snowflake", "MongoDB"]
    
    results = await enrich_competitors_with_solutionsreview(
        competitor_names=companies,
        analyze_news=True
    )
    
    print(f"\nEnriched {len(companies)} specific companies:")
    for company in companies:
        company_result = next((r for r in results.get('results', []) if r['company'] == company), None)
        if company_result:
            print(f"  • {company}: {company_result.get('articles_saved', 0)} articles")


async def example_3_single_company_scraping():
    """Example 3: Direct scraping of a single company"""
    
    print("\n🚀 Example 3: Direct scraping for single company")
    print("=" * 80)
    
    company_name = "Salesforce"
    
    # Initialize scraper
    scraper = SolutionsReviewScraper()
    
    # Search for articles
    print(f"🔍 Searching for '{company_name}' articles on SolutionsReview...")
    articles = await scraper.scrape_company_news(company_name, max_articles=5)
    
    print(f"\n📰 Found {len(articles)} articles:")
    for i, article in enumerate(articles, 1):
        print(f"  {i}. {article.get('title', 'No title')[:60]}...")
        print(f"     📅 {article.get('date', 'No date')}")
        print(f"     🔗 {article.get('url', 'No URL')}")
        print(f"     📝 {article.get('content', 'No content')[:100]}...")
        print()


async async def example_4_without_ai_analysis():
    """Example 4: Run enrichment without AI analysis (faster)"""
    
    print("\n🚀 Example 4: Enrichment without AI analysis")
    print("=" * 80)
    
    # Get few companies for quick test
    db_ops = SolutionsReviewDataOperations(analyze_news=False)
    all_companies = db_ops.get_all_competitor_names()
    test_companies = all_companies[:3] if len(all_companies) > 3 else all_companies
    
    print(f"Testing with {len(test_companies)} companies (no AI analysis)...")
    
    results = await enrich_competitors_with_solutionsreview(
        competitor_names=test_companies,
        analyze_news=False  # Disable AI analysis for speed
    )
    
    print(f"Processed {results.get('companies_processed', 0)} companies without AI analysis")
    print(f"Total articles saved: {results.get('total_articles_saved', 0)}")


async def main():
    """Run all examples"""
    
    print("🎯 SOLUTIONSREVIEW SERVICE EXAMPLES")
    print("=" * 80)
    print("This will demonstrate different ways to use the SolutionsReview service")
    print()
    
    # Example 1: Enrich all competitors (main functionality)
    await example_1_enrich_all_competitors()
    
    # Example 2: Specific companies only
    await example_2_specific_companies()
    
    # Example 3: Direct scraping demo
    await example_3_single_company_scraping()
    
    # Example 4: Without AI analysis
    await example_4_without_ai_analysis()
    
    print("\n🎉 All examples completed!")
    print("Check your competitors_news table for the new articles")


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())
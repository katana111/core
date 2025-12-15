"""
GlobeNewswire enrichment service for batch processing competitor news.
Orchestrates scraping and saving news articles for all competitors.
"""

import asyncio
import time
from typing import List, Dict, Optional
from services.globenewswire.scraper import GlobeNewswireScraper
from services.globenewswire.db_operations import GlobeNewswireDataOperations


async def enrich_competitors_with_globenewswire(
    competitor_names: List[str] = None, 
    analyze_news: bool = True,
    max_articles_per_company: int = 10
) -> Dict:
    """
    Enrich competitors with GlobeNewswire news articles
    
    Args:
        competitor_names: List of competitor names to process (if None, processes all)
        analyze_news: Whether to use AI analysis for articles
        max_articles_per_company: Maximum articles to scrape per company
        
    Returns:
        Dictionary with processing results and statistics
    """
    start_time = time.time()
    
    # Initialize components
    db_ops = GlobeNewswireDataOperations(analyze_news=analyze_news)
    
    # Get competitors to process
    if competitor_names:
        competitors = []
        for name in competitor_names:
            competitor = db_ops.get_competitor_by_name(name)
            if competitor:
                competitors.append(competitor)
            else:
                print(f"⚠️  Competitor '{name}' not found in database")
    else:
        competitors = db_ops.get_all_competitors()
    
    if not competitors:
        return {
            'status': 'error',
            'message': 'No competitors found to process',
            'total_articles_found': 0,
            'total_articles_saved': 0,
            'companies_processed': 0,
            'processing_time_seconds': 0
        }
    
    print(f"🚀 Starting GlobeNewswire enrichment for {len(competitors)} competitors...")
    print(f"🤖 AI analysis: {'enabled' if analyze_news else 'disabled'}")
    print(f"📊 Max articles per company: {max_articles_per_company}")
    
    total_articles_found = 0
    total_articles_saved = 0
    companies_processed = 0
    errors = []
    
    # Process each competitor
    async with GlobeNewswireScraper(headless=True, delay_between_requests=2.0) as scraper:
        for i, competitor in enumerate(competitors, 1):
            try:
                print(f"\\n🏢 Processing {i}/{len(competitors)}: {competitor['name']}")
                
                # Scrape articles for this competitor
                articles = await scraper.search_company_news(
                    competitor['name'],
                    max_articles=max_articles_per_company
                )
                
                if not articles:
                    print(f"📰 No articles found for {competitor['name']}")
                    companies_processed += 1
                    continue
                
                print(f"📰 Found {len(articles)} articles for {competitor['name']}")
                total_articles_found += len(articles)
                
                # Save articles to database
                save_result = db_ops.save_competitor_news(competitor['name'], articles)
                
                if save_result['success']:
                    total_articles_saved += save_result['saved_count']
                    print(f"✅ Saved {save_result['saved_count']}/{len(articles)} articles for {competitor['name']}")
                else:
                    print(f"❌ Failed to save articles for {competitor['name']}: {save_result['message']}")
                    errors.append(f"{competitor['name']}: {save_result['message']}")
                
                companies_processed += 1
                
                # Add delay between companies to be respectful to the website
                if i < len(competitors):
                    await asyncio.sleep(3.0)
                
            except Exception as e:
                error_msg = f"Error processing {competitor['name']}: {str(e)}"
                print(f"❌ {error_msg}")
                errors.append(error_msg)
                companies_processed += 1
                continue
    
    # Calculate final statistics
    processing_time = time.time() - start_time
    success_rate = (total_articles_saved / total_articles_found * 100) if total_articles_found > 0 else 0
    
    # Print final summary
    print(f"\\n" + "=" * 80)
    print("🎉 GLOBENEWSWIRE ENRICHMENT COMPLETE!")
    print("=" * 80)
    print(f"⏱️  Total processing time: {processing_time:.2f} seconds")
    print(f"🏢 Companies processed: {companies_processed}")
    print(f"📰 Total articles found: {total_articles_found}")
    print(f"💾 Total articles saved: {total_articles_saved}")
    print(f"✅ Success rate: {success_rate:.1f}%")
    
    if errors:
        print(f"❌ Errors encountered: {len(errors)}")
        for error in errors[:5]:  # Show first 5 errors
            print(f"   - {error}")
        if len(errors) > 5:
            print(f"   ... and {len(errors) - 5} more errors")
    
    print("=" * 80)
    
    return {
        'status': 'completed',
        'message': f'Processed {companies_processed} companies, saved {total_articles_saved} articles',
        'total_articles_found': total_articles_found,
        'total_articles_saved': total_articles_saved,
        'articles_skipped': total_articles_found - total_articles_saved,
        'companies_processed': companies_processed,
        'success_rate': success_rate,
        'processing_time_seconds': processing_time,
        'errors': errors,
        'source': 'globenewswire'
    }


class GlobeNewswireEnrichmentService:
    """Service class for batch GlobeNewswire enrichment operations"""
    
    def __init__(self, analyze_news: bool = True, max_articles_per_company: int = 10):
        """
        Initialize the enrichment service
        
        Args:
            analyze_news: Whether to use AI analysis
            max_articles_per_company: Maximum articles to scrape per company
        """
        self.analyze_news = analyze_news
        self.max_articles_per_company = max_articles_per_company
        self.db_ops = GlobeNewswireDataOperations(analyze_news=analyze_news)
    
    async def enrich_all_competitors(self) -> Dict:
        """
        Enrich all competitors in the database
        
        Returns:
            Dictionary with processing results
        """
        return await enrich_competitors_with_globenewswire(
            competitor_names=None,
            analyze_news=self.analyze_news,
            max_articles_per_company=self.max_articles_per_company
        )
    
    async def enrich_specific_competitors(self, competitor_names: List[str]) -> Dict:
        """
        Enrich specific competitors
        
        Args:
            competitor_names: List of competitor names to process
            
        Returns:
            Dictionary with processing results
        """
        return await enrich_competitors_with_globenewswire(
            competitor_names=competitor_names,
            analyze_news=self.analyze_news,
            max_articles_per_company=self.max_articles_per_company
        )
    
    async def enrich_competitor(self, competitor_name: str) -> Dict:
        """
        Enrich a single competitor
        
        Args:
            competitor_name: Name of the competitor to process
            
        Returns:
            Dictionary with processing results
        """
        return await self.enrich_specific_competitors([competitor_name])
    
    def get_statistics(self, competitor_name: str = None) -> Dict:
        """
        Get enrichment statistics
        
        Args:
            competitor_name: Optional competitor name to filter by
            
        Returns:
            Dictionary with statistics
        """
        return self.db_ops.get_save_statistics(competitor_name)
    
    def get_recent_articles(self, competitor_name: str = None, days: int = 30, limit: int = 10) -> List[Dict]:
        """
        Get recent articles from database
        
        Args:
            competitor_name: Optional competitor name to filter by
            days: Number of days to look back
            limit: Maximum number of articles to return
            
        Returns:
            List of article dictionaries
        """
        return self.db_ops.get_recent_news(competitor_name, days, limit)


# Example usage and testing
async def main():
    """Example usage of the GlobeNewswire enrichment service"""
    
    # Test with a single competitor
    print("🧪 Testing GlobeNewswire enrichment with Seon...")
    
    result = await enrich_competitors_with_globenewswire(
        competitor_names=['Seon'],
        analyze_news=True,
        max_articles_per_company=5
    )
    
    print(f"\\nTest Results:")
    print(f"Status: {result['status']}")
    print(f"Articles found: {result['total_articles_found']}")
    print(f"Articles saved: {result['total_articles_saved']}")
    print(f"Processing time: {result['processing_time_seconds']:.2f} seconds")
    
    # Show recent articles
    print(f"\\n📰 Recent GlobeNewswire articles:")
    db_ops = GlobeNewswireDataOperations()
    recent_articles = db_ops.get_recent_news('Seon', days=30, limit=5)
    
    for i, article in enumerate(recent_articles, 1):
        print(f"{i}. {article['title']}")
        print(f"   Date: {article['published_date']}")
        print(f"   Sentiment: {article['sentiment']}")


if __name__ == "__main__":
    asyncio.run(main())
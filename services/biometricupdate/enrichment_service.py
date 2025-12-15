"""
BiometricUpdate Enrichment Service
Processes all competitors to find and analyze news articles from biometricupdate.com
"""

import asyncio
import time
from typing import Dict, List
from services.biometricupdate.scraper import BiometricUpdateScraper
from services.biometricupdate.db_operations import BiometricUpdateDataOperations


class BiometricUpdateEnrichmentService:
    """Service to enrich all competitors with BiometricUpdate news articles"""
    
    def __init__(self, analyze_news: bool = True):
        """
        Initialize the enrichment service
        
        Args:
            analyze_news: Whether to use AI to analyze articles (default: True)
        """
        self.scraper = BiometricUpdateScraper()
        self.db_ops = BiometricUpdateDataOperations(analyze_news=analyze_news)
    
    async def _process_competitor(self, company_name: str) -> Dict:
        """
        Process a single competitor
        
        Args:
            company_name: Name of the company to process
            
        Returns:
            Dictionary with processing results
        """
        print(f"\n🔍 Searching for articles about '{company_name}'...")
        
        try:
            # Scrape articles from BiometricUpdate
            articles = await self.scraper.scrape_company_news(company_name)
            
            if not articles:
                print(f"  ⚠ No articles found for '{company_name}'")
                return {
                    'company': company_name,
                    'status': 'no_articles',
                    'articles_found': 0,
                    'articles_saved': 0,
                    'articles_skipped': 0
                }
            
            print(f"  📰 Found {len(articles)} articles")
            
            # Save to database
            save_result = self.db_ops.save_company_articles(company_name, articles)
            
            if 'error' in save_result:
                print(f"  ❌ Error: {save_result['error']}")
                return {
                    'company': company_name,
                    'status': 'error',
                    'error': save_result['error'],
                    'articles_found': len(articles),
                    'articles_saved': 0,
                    'articles_skipped': 0
                }
            
            print(f"  ✅ Saved {save_result['saved']}/{save_result['total']} articles")
            if save_result['skipped'] > 0:
                print(f"     (Skipped {save_result['skipped']} duplicates)")
            
            return {
                'company': company_name,
                'status': 'success',
                'articles_found': save_result['total'],
                'articles_saved': save_result['saved'],
                'articles_skipped': save_result['skipped'],
                'competitor_id': save_result.get('competitor_id'),
                'competitor_name': save_result.get('competitor_name')
            }
            
        except Exception as e:
            print(f"  ❌ Error processing '{company_name}': {str(e)}")
            return {
                'company': company_name,
                'status': 'error',
                'error': str(e),
                'articles_found': 0,
                'articles_saved': 0,
                'articles_skipped': 0
            }
        
        finally:
            # Rate limiting
            await asyncio.sleep(2)
    
    async def enrich_all_competitors(self, competitor_names: List[str] = None) -> Dict:
        """
        Enrich all competitors with BiometricUpdate articles
        
        Args:
            competitor_names: List of company names to process (optional)
            
        Returns:
            Dictionary with overall statistics
        """
        start_time = time.time()
        
        # Get competitor names if not provided
        if competitor_names is None:
            print("🔍 Fetching competitor names from database...")
            competitor_names = self.db_ops.get_all_competitor_names()
        
        if not competitor_names:
            return {
                'status': 'error',
                'message': 'No competitors found in database'
            }
        
        print(f"📊 Processing {len(competitor_names)} competitors for BiometricUpdate articles...")
        print("=" * 80)
        
        results = []
        
        # Process each competitor
        for i, company_name in enumerate(competitor_names, 1):
            print(f"\n[{i}/{len(competitor_names)}] Processing: {company_name}")
            
            result = await self._process_competitor(company_name)
            results.append(result)
        
        # Calculate statistics
        stats = self._calculate_statistics(results)
        end_time = time.time()
        
        # Print summary
        print("\n" + "=" * 80)
        print("🎉 BIOMETRICUPDATE ENRICHMENT COMPLETE!")
        print("=" * 80)
        print(f"⏱️  Total time: {end_time - start_time:.2f} seconds")
        print(f"🏢 Companies processed: {stats['companies_processed']}")
        print(f"📰 Total articles found: {stats['total_articles_found']}")
        print(f"💾 Articles saved: {stats['total_articles_saved']}")
        print(f"⚠️  Articles skipped: {stats['total_articles_skipped']}")
        print(f"✅ Success rate: {stats['success_rate']:.1f}%")
        
        if stats['companies_with_articles'] > 0:
            print(f"📈 Average articles per company: {stats['avg_articles_per_company']:.1f}")
        
        if stats['errors'] > 0:
            print(f"❌ Errors: {stats['errors']}")
        
        stats['processing_time'] = end_time - start_time
        stats['results'] = results
        
        return stats
    
    def _calculate_statistics(self, results: List[Dict]) -> Dict:
        """Calculate enrichment statistics"""
        
        total_companies = len(results)
        successful = len([r for r in results if r['status'] == 'success'])
        errors = len([r for r in results if r['status'] == 'error'])
        no_articles = len([r for r in results if r['status'] == 'no_articles'])
        
        total_articles_found = sum(r.get('articles_found', 0) for r in results)
        total_articles_saved = sum(r.get('articles_saved', 0) for r in results)
        total_articles_skipped = sum(r.get('articles_skipped', 0) for r in results)
        
        companies_with_articles = len([r for r in results if r.get('articles_found', 0) > 0])
        
        success_rate = (successful / total_companies * 100) if total_companies > 0 else 0
        avg_articles_per_company = (total_articles_found / companies_with_articles) if companies_with_articles > 0 else 0
        
        return {
            'status': 'completed',
            'companies_processed': total_companies,
            'successful': successful,
            'errors': errors,
            'no_articles': no_articles,
            'companies_with_articles': companies_with_articles,
            'total_articles_found': total_articles_found,
            'total_articles_saved': total_articles_saved,
            'total_articles_skipped': total_articles_skipped,
            'success_rate': success_rate,
            'avg_articles_per_company': avg_articles_per_company
        }


# Quick usage function for convenience
async def enrich_competitors_with_biometricupdate(competitor_names: List[str] = None, analyze_news: bool = True):
    """
    Quick function to enrich competitors with BiometricUpdate articles
    
    Args:
        competitor_names: List of company names to process (optional)
        analyze_news: Whether to use AI analysis (default: True)
    """
    service = BiometricUpdateEnrichmentService(analyze_news=analyze_news)
    return await service.enrich_all_competitors(competitor_names)
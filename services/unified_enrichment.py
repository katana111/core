"""
Unified News Enrichment Service
Orchestrates all news services to provide comprehensive competitor intelligence
"""

import asyncio
import time
from typing import Dict, List, Optional
from datetime import datetime
from services.parsersvc.enrichment_service import CompetitorEnrichmentService
from services.solutionsreview.enrichment_service import enrich_competitors_with_solutionsreview
from services.biometricupdate.enrichment_service import enrich_competitors_with_biometricupdate
from services.globenewswire.enrichment_service import enrich_competitors_with_globenewswire
from database import get_db


async def enrich_competitors_with_parsersvc(competitor_names: List[str] = None, analyze_news: bool = True) -> Dict:
    """
    Wrapper function to make parsersvc compatible with unified interface
    
    Args:
        competitor_names: List of company names (not used by parsersvc - processes all)
        analyze_news: Whether to use AI analysis
        
    Returns:
        Enrichment results in unified format
    """
    service = CompetitorEnrichmentService(headless=True, delay_between_requests=2.0)
    
    # Run parsersvc enrichment (processes all competitors)
    result = service.enrich_all_competitors(limit=None)
    
    # Convert to unified format
    return {
        'status': 'completed',
        'total_articles_found': 0,  # ParsersVC doesn't return this stat
        'total_articles_saved': 0,  # ParsersVC doesn't return this stat 
        'total_articles_skipped': 0,  # ParsersVC doesn't return this stat
        'companies_processed': result.get('processed', 0),
        'success_rate': (result.get('successful', 0) / result.get('processed', 1)) * 100 if result.get('processed', 0) > 0 else 0,
        'source': 'parsersvc'
    }


class UnifiedNewsEnrichmentService:
    """Unified service to run all news enrichment sources"""
    
    def __init__(self, analyze_news: bool = True):
        """
        Initialize the unified enrichment service
        
        Args:
            analyze_news: Whether to use AI analysis for all services
        """
        self.analyze_news = analyze_news
        self.db = get_db()
    
    def get_all_competitor_names(self) -> List[str]:
        """Get all competitor names from database"""
        query = "SELECT DISTINCT name FROM competitors WHERE name IS NOT NULL ORDER BY name"
        
        with self.db.get_cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            
            return [row[0] for row in rows]
    
    async def enrich_from_single_source(self, source: str, competitor_names: List[str] = None) -> Dict:
        """
        Enrich from a single news source
        
        Args:
            source: One of 'parsersvc', 'solutionsreview', 'biometricupdate', 'globenewswire'
            competitor_names: List of company names to process
            
        Returns:
            Enrichment results dictionary
        """
        print(f"\n🔍 Starting enrichment from {source.upper()}...")
        
        if source.lower() == 'parsersvc':
            return await enrich_competitors_with_parsersvc(
                competitor_names=competitor_names,
                analyze_news=self.analyze_news
            )
        elif source.lower() == 'solutionsreview':
            return await enrich_competitors_with_solutionsreview(
                competitor_names=competitor_names,
                analyze_news=self.analyze_news
            )
        elif source.lower() == 'biometricupdate':
            return await enrich_competitors_with_biometricupdate(
                competitor_names=competitor_names,
                analyze_news=self.analyze_news
            )
        elif source.lower() == 'globenewswire':
            return await enrich_competitors_with_globenewswire(
                competitor_names=competitor_names,
                analyze_news=self.analyze_news
            )
        else:
            raise ValueError(f"Unknown source: {source}. Must be one of: parsersvc, solutionsreview, biometricupdate, globenewswire")
    
    async def enrich_all_sources(self, 
                                competitor_names: List[str] = None,
                                sources: List[str] = None,
                                run_parallel: bool = False) -> Dict:
        """
        Enrich from all configured news sources
        
        Args:
            competitor_names: List of company names to process (optional)
            sources: List of sources to use (optional, defaults to all)
            run_parallel: Whether to run sources in parallel (faster but more intensive)
            
        Returns:
            Comprehensive enrichment results
        """
        start_time = time.time()
        
        # Get competitor names if not provided
        if competitor_names is None:
            print("🔍 Fetching competitor names from database...")
            competitor_names = self.get_all_competitor_names()
        
        if not competitor_names:
            return {
                'status': 'error',
                'message': 'No competitors found in database'
            }
        
        # Default to all sources if none specified
        if sources is None:
            sources = ['parsersvc', 'solutionsreview', 'biometricupdate', 'globenewswire']
        
        print(f"📊 UNIFIED NEWS ENRICHMENT STARTING")
        print(f"Companies: {len(competitor_names)}")
        print(f"Sources: {', '.join(s.upper() for s in sources)}")
        print(f"AI Analysis: {'Enabled' if self.analyze_news else 'Disabled'}")
        print(f"Execution: {'Parallel' if run_parallel else 'Sequential'}")
        print("=" * 80)
        
        source_results = {}
        
        if run_parallel:
            # Run all sources in parallel (faster but more resource intensive)
            print("⚡ Running sources in parallel...")
            tasks = []
            for source in sources:
                task = self.enrich_from_single_source(source, competitor_names)
                tasks.append(task)
            
            results_list = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results_list):
                source = sources[i]
                if isinstance(result, Exception):
                    print(f"❌ {source.upper()} failed: {str(result)}")
                    source_results[source] = {
                        'status': 'error',
                        'error': str(result)
                    }
                else:
                    source_results[source] = result
        else:
            # Run sources sequentially (safer, less resource intensive)
            print("🔄 Running sources sequentially...")
            for source in sources:
                try:
                    result = await self.enrich_from_single_source(source, competitor_names)
                    source_results[source] = result
                    
                    # Brief pause between sources
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    print(f"❌ {source.upper()} failed: {str(e)}")
                    source_results[source] = {
                        'status': 'error',
                        'error': str(e)
                    }
        
        # Calculate overall statistics
        overall_stats = self._calculate_overall_statistics(source_results, competitor_names)
        end_time = time.time()
        overall_stats['processing_time'] = end_time - start_time
        
        # Print comprehensive summary
        self._print_comprehensive_summary(overall_stats, source_results)
        
        return {
            'status': 'completed',
            'overall_stats': overall_stats,
            'source_results': source_results,
            'competitors_processed': competitor_names,
            'execution_mode': 'parallel' if run_parallel else 'sequential'
        }
    
    def _calculate_overall_statistics(self, source_results: Dict, competitor_names: List[str]) -> Dict:
        """Calculate comprehensive statistics across all sources"""
        
        total_articles_found = 0
        total_articles_saved = 0
        total_articles_skipped = 0
        successful_sources = 0
        failed_sources = 0
        
        source_stats = {}
        
        for source, result in source_results.items():
            if result.get('status') == 'completed':
                successful_sources += 1
                articles_found = result.get('total_articles_found', 0)
                articles_saved = result.get('total_articles_saved', 0)
                articles_skipped = result.get('total_articles_skipped', 0)
                
                total_articles_found += articles_found
                total_articles_saved += articles_saved
                total_articles_skipped += articles_skipped
                
                source_stats[source] = {
                    'found': articles_found,
                    'saved': articles_saved,
                    'skipped': articles_skipped,
                    'success_rate': result.get('success_rate', 0)
                }
            else:
                failed_sources += 1
                source_stats[source] = {
                    'found': 0,
                    'saved': 0,
                    'skipped': 0,
                    'success_rate': 0,
                    'error': result.get('error', 'Unknown error')
                }
        
        overall_success_rate = (successful_sources / len(source_results) * 100) if source_results else 0
        
        return {
            'companies_processed': len(competitor_names),
            'sources_total': len(source_results),
            'sources_successful': successful_sources,
            'sources_failed': failed_sources,
            'overall_success_rate': overall_success_rate,
            'total_articles_found': total_articles_found,
            'total_articles_saved': total_articles_saved,
            'total_articles_skipped': total_articles_skipped,
            'source_breakdown': source_stats
        }
    
    def _print_comprehensive_summary(self, overall_stats: Dict, source_results: Dict):
        """Print detailed summary of all enrichment results"""
        
        print("\\n" + "=" * 80)
        print("🎉 UNIFIED NEWS ENRICHMENT COMPLETE!")
        print("=" * 80)
        
        # Overall statistics
        print(f"⏱️  Total processing time: {overall_stats.get('processing_time', 0):.2f} seconds")
        print(f"🏢 Companies processed: {overall_stats['companies_processed']}")
        print(f"📊 Sources used: {overall_stats['sources_total']} ({overall_stats['sources_successful']} successful, {overall_stats['sources_failed']} failed)")
        print(f"✅ Overall success rate: {overall_stats['overall_success_rate']:.1f}%")
        print(f"📰 Total articles found: {overall_stats['total_articles_found']}")
        print(f"💾 Total articles saved: {overall_stats['total_articles_saved']}")
        print(f"⚠️  Total articles skipped: {overall_stats['total_articles_skipped']}")
        
        # Per-source breakdown
        print(f"\\n📋 SOURCE BREAKDOWN:")
        for source, stats in overall_stats['source_breakdown'].items():
            if 'error' in stats:
                print(f"   ❌ {source.upper()}: Failed - {stats['error']}")
            else:
                print(f"   ✅ {source.upper()}: {stats['saved']} saved, {stats['found']} found, {stats['success_rate']:.1f}% success")
        
        # Data quality insights
        if overall_stats['total_articles_saved'] > 0:
            skip_rate = (overall_stats['total_articles_skipped'] / (overall_stats['total_articles_found']) * 100) if overall_stats['total_articles_found'] > 0 else 0
            print(f"\\n📈 DATA QUALITY:")
            print(f"   Content relevance: {100-skip_rate:.1f}% of found articles were business-relevant")
            print(f"   Average articles per company: {overall_stats['total_articles_saved'] / overall_stats['companies_processed']:.1f}")
        
        print("\\n💡 TIP: Check your competitors_news table for the enriched data!")
        print("=" * 80)


# Convenience functions for different execution patterns
async def enrich_all_competitors_unified(competitor_names: List[str] = None, 
                                       sources: List[str] = None,
                                       analyze_news: bool = True,
                                       run_parallel: bool = False) -> Dict:
    """
    Quick function to run unified enrichment on all competitors
    
    Args:
        competitor_names: List of company names (optional)
        sources: List of sources to use (optional, defaults to all)
        analyze_news: Whether to use AI analysis
        run_parallel: Whether to run sources in parallel
    """
    service = UnifiedNewsEnrichmentService(analyze_news=analyze_news)
    return await service.enrich_all_sources(
        competitor_names=competitor_names,
        sources=sources,
        run_parallel=run_parallel
    )


async def quick_news_update(competitor_names: List[str] = None) -> Dict:
    """
    Quick news update - run all sources sequentially with AI analysis
    
    Args:
        competitor_names: List of company names (optional)
    """
    return await enrich_all_competitors_unified(
        competitor_names=competitor_names,
        analyze_news=True,
        run_parallel=False
    )


async def fast_news_update(competitor_names: List[str] = None) -> Dict:
    """
    Fast news update - run all sources in parallel with AI analysis
    Warning: More resource intensive
    
    Args:
        competitor_names: List of company names (optional)
    """
    return await enrich_all_competitors_unified(
        competitor_names=competitor_names,
        analyze_news=True,
        run_parallel=True
    )


async def basic_news_update(competitor_names: List[str] = None) -> Dict:
    """
    Basic news update - run all sources without AI analysis (faster)
    
    Args:
        competitor_names: List of company names (optional)
    """
    return await enrich_all_competitors_unified(
        competitor_names=competitor_names,
        analyze_news=False,
        run_parallel=False
    )
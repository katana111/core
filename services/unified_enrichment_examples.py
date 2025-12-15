"""
Example usage of Unified News Enrichment Service
Demonstrates how to run all 4 news services together for comprehensive competitor intelligence
Coordinates: ParsersVC, SolutionsReview, BiometricUpdate, and GlobeNewswire
"""

import asyncio
from services.unified_enrichment import (
    enrich_all_competitors_unified,
    quick_news_update,
    fast_news_update,
    basic_news_update,
    UnifiedNewsEnrichmentService
)


async def example_1_quick_update():
    """Example 1: Quick comprehensive update (all sources, AI analysis, sequential)"""
    
    print("🚀 Example 1: Quick comprehensive news update")
    print("=" * 80)
    print("This will run all news sources sequentially with AI analysis")
    print()
    
    results = await quick_news_update()
    
    print(f"\n📊 RESULTS SUMMARY:")
    print(f"   Overall success rate: {results['overall_stats']['overall_success_rate']:.1f}%")
    print(f"   Total articles saved: {results['overall_stats']['total_articles_saved']}")
    print(f"   Processing time: {results['overall_stats']['processing_time']:.2f} seconds")


async def example_2_specific_companies():
    """Example 2: Enrich specific companies only"""
    
    print("\n🚀 Example 2: Enrich specific companies")
    print("=" * 80)
    
    # Target specific companies
    target_companies = ["Seon", "LexisNexis"]
    
    results = await enrich_all_competitors_unified(
        competitor_names=target_companies,
        analyze_news=True,
        run_parallel=False
    )
    
    print(f"Enriched {len(target_companies)} companies:")
    for company in target_companies:
        print(f"  • {company}: Data updated from all sources")


async def example_3_fast_parallel_update():
    """Example 3: Fast parallel update (higher resource usage)"""
    
    print("\n🚀 Example 3: Fast parallel update")
    print("=" * 80)
    print("⚠️  Warning: This runs all sources in parallel (more intensive)")
    
    results = await fast_news_update()
    
    print(f"Fast update completed in {results['overall_stats']['processing_time']:.2f} seconds")
    print(f"Execution mode: {results['execution_mode']}")


async def example_4_selective_sources():
    """Example 4: Run only specific news sources"""
    
    print("\n🚀 Example 4: Selective news sources")
    print("=" * 80)
    
    # Only run specific sources (e.g., press release focused sources)
    sources = ['biometricupdate', 'globenewswire']
    
    results = await enrich_all_competitors_unified(
        sources=sources,
        analyze_news=True,
        run_parallel=False
    )
    
    print(f"Used sources: {', '.join(sources)}")
    print(f"Articles saved: {results['overall_stats']['total_articles_saved']}")


async def example_5_basic_without_ai():
    """Example 5: Basic update without AI analysis (fastest)"""
    
    print("\n🚀 Example 5: Basic update without AI analysis")
    print("=" * 80)
    
    results = await basic_news_update()
    
    print(f"Basic update (no AI) completed in {results['overall_stats']['processing_time']:.2f} seconds")
    print(f"Articles saved: {results['overall_stats']['total_articles_saved']}")


async def example_6_single_source():
    """Example 6: Run single source through unified service"""
    
    print("\n🚀 Example 6: Single source enrichment")
    print("=" * 80)
    
    service = UnifiedNewsEnrichmentService(analyze_news=True)
    
    # Run only BiometricUpdate
    result = await service.enrich_from_single_source('biometricupdate')
    
    print(f"BiometricUpdate only:")
    print(f"   Articles found: {result.get('total_articles_found', 0)}")
    print(f"   Articles saved: {result.get('total_articles_saved', 0)}")
    print(f"   Success rate: {result.get('success_rate', 0):.1f}%")


async def example_7_comprehensive_monitoring():
    """Example 7: Comprehensive business intelligence monitoring"""
    
    print("\n🚀 Example 7: Comprehensive monitoring dashboard")
    print("=" * 80)
    
    service = UnifiedNewsEnrichmentService(analyze_news=True)
    
    # Get current competitors
    competitors = service.get_all_competitor_names()
    print(f"📊 Monitoring {len(competitors)} competitors:")
    for i, comp in enumerate(competitors, 1):
        print(f"   {i}. {comp}")
    
    # Run comprehensive enrichment
    results = await service.enrich_all_sources(
        competitor_names=competitors,
        run_parallel=False  # Safe for production
    )
    
    # Detailed source analysis
    print(f"\n📈 DETAILED SOURCE PERFORMANCE:")
    for source, stats in results['overall_stats']['source_breakdown'].items():
        if 'error' not in stats:
            efficiency = (stats['saved'] / stats['found'] * 100) if stats['found'] > 0 else 0
            print(f"   {source.upper()}:")
            print(f"     📰 Found: {stats['found']} articles")
            print(f"     💾 Saved: {stats['saved']} articles") 
            print(f"     📊 Efficiency: {efficiency:.1f}% (relevance filter)")
            print(f"     ✅ Success: {stats['success_rate']:.1f}%")


async def main():
    """Run all examples"""
    
    print("🎯 UNIFIED NEWS ENRICHMENT SERVICE EXAMPLES")
    print("=" * 80)
    print("This will demonstrate the unified service that orchestrates all news sources")
    print()
    
    # Example 1: Quick comprehensive update
    await example_1_quick_update()
    
    # Example 2: Specific companies
    await example_2_specific_companies()
    
    # Example 3: Fast parallel (comment out if too intensive)
    # await example_3_fast_parallel_update()
    
    # Example 4: Selective sources
    await example_4_selective_sources()
    
    # Example 5: Basic without AI
    await example_5_basic_without_ai()
    
    # Example 6: Single source
    await example_6_single_source()
    
    # Example 7: Comprehensive monitoring
    await example_7_comprehensive_monitoring()
    
    print("\n🎉 All unified enrichment examples completed!")
    print("💡 The unified service provides comprehensive competitor intelligence")
    print("   by combining ParsersVC, SolutionsReview, and BiometricUpdate data")


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())
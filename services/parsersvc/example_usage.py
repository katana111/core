"""
Example usage of Parsers.vc scraper
Demonstrates how to scrape single company and batch process
"""

import sys
sys.path.insert(0, '/Users/katerynahunko/insiderai/core')

from database import get_db
from services.parsersvc.scraper import ParsersVCScraper
from services.parsersvc.db_operations import ParsersVCDataOperations
from services.parsersvc.enrichment_service import CompetitorEnrichmentService


def example_single_company():
    """Example: Scrape a single company"""
    print("=" * 80)
    print("EXAMPLE 1: Scrape single company from Parsers.vc")
    print("=" * 80)
    
    # Initialize scraper
    scraper = ParsersVCScraper(headless=True)
    
    # Scrape a company (e.g., seon.io)
    website = "seon.io"
    print(f"\nScraping: {website}")
    
    data = scraper.scrape_company(website)
    
    if data:
        print("\nScraped data:")
        print(f"  Website: {data.get('website')}")
        print(f"  Location: {data.get('location')}")
        print(f"  Employees: {data.get('employees')}")
        print(f"  Total Raised: ${data.get('total_raised'):,.0f}" if data.get('total_raised') else "  Total Raised: N/A")
        print(f"  Founded: {data.get('founded_year')}")
        print(f"  Scraped at: {data.get('scraped_at')}")
    else:
        print("Failed to scrape company")


def example_save_to_database():
    """Example: Scrape and save to database"""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Scrape and save to database")
    print("=" * 80)
    
    # Initialize database
    db = get_db()
    db.initialize()
    
    # Initialize scraper and db operations
    scraper = ParsersVCScraper(headless=True)
    db_ops = ParsersVCDataOperations()
    
    # Scrape company
    website = "seon.io"
    print(f"\nScraping: {website}")
    
    data = scraper.scrape_company(website)
    
    if data:
        print("\nSaving to database...")
        success = db_ops.save_competitor(data)
        
        if success:
            print("✓ Successfully saved to database")
        else:
            print("✗ Failed to save to database")
    else:
        print("Failed to scrape company")


def example_batch_enrichment():
    """Example: Batch enrich all competitors"""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Batch enrich all competitors")
    print("=" * 80)
    
    # Initialize database
    db = get_db()
    db.initialize()
    
    # Create enrichment service
    service = CompetitorEnrichmentService(
        headless=True,
        delay_between_requests=2.0  # 2 second delay between requests
    )
    
    # Enrich first 5 competitors (for testing)
    print("\nEnriching first 5 competitors...")
    results = service.enrich_all_competitors(limit=5)
    
    print("\nResults:")
    print(f"  Total: {results['total']}")
    print(f"  Processed: {results['processed']}")
    print(f"  Successful: {results['successful']}")
    print(f"  Failed: {results['failed']}")


def example_batch_enrichment_all():
    """Example: Batch enrich ALL competitors (no limit)"""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Batch enrich ALL competitors (WARNING: May take long time)")
    print("=" * 80)
    
    # Initialize database
    db = get_db()
    db.initialize()
    
    # Create enrichment service
    service = CompetitorEnrichmentService(
        headless=True,
        delay_between_requests=2.0
    )
    
    # Enrich all competitors
    print("\nEnriching ALL competitors...")
    results = service.enrich_all_competitors(limit=None)
    
    print("\nFinal results:")
    print(f"  Total: {results['total']}")
    print(f"  Processed: {results['processed']}")
    print(f"  Successful: {results['successful']}")
    print(f"  Failed: {results['failed']}")


if __name__ == "__main__":
    # Run examples
    example_single_company()
    example_save_to_database()
    example_batch_enrichment()
    
    # Uncomment to run full batch enrichment
    # example_batch_enrichment_all()

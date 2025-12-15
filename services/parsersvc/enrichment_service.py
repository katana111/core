"""
Batch processor to enrich competitors data from Parsers.vc
Loops through all competitors in database and scrapes parsers.vc data
"""

import re
import time
from typing import List, Dict
from database import get_db
from services.parsersvc.scraper import ParsersVCScraper
from services.parsersvc.db_operations import ParsersVCDataOperations


class CompetitorEnrichmentService:
    """Service to batch process and enrich competitor data"""
    
    def __init__(self, headless: bool = True, delay_between_requests: float = 2.0):
        """
        Initialize enrichment service
        
        Args:
            headless: Run browser in headless mode
            delay_between_requests: Delay in seconds between each request
        """
        self.scraper = ParsersVCScraper(headless=headless)
        self.db_ops = ParsersVCDataOperations()
        self.delay = delay_between_requests
    
    def _clean_website(self, website: str) -> str:
        """
        Clean website URL - remove protocol and trailing slashes
        
        Args:
            website: Raw website URL
            
        Returns:
            Clean website domain
        """
        if not website:
            return ""
        
        # Remove protocol
        website = re.sub(r'^https?://', '', website)
        # Remove www prefix
        website = re.sub(r'^www\.', '', website)
        # Remove trailing slash
        website = website.rstrip('/')
        # Take only domain (remove path)
        website = website.split('/')[0]
        
        return website.strip()
    
    def enrich_competitor(self, competitor: Dict) -> bool:
        """
        Enrich a single competitor with parsers.vc data
        
        Args:
            competitor: Dictionary with id, name, website
            
        Returns:
            True if successful, False otherwise
        """
        try:
            competitor_id = competitor['id']
            name = competitor['name']
            website = competitor['website']
            
            # Clean website
            clean_website = self._clean_website(website)
            
            if not clean_website:
                print(f"[{competitor_id}] {name}: Invalid website")
                return False
            
            print(f"\n[{competitor_id}] Processing: {name} ({clean_website})")
            
            # Scrape parsers.vc
            scraped_data = self.scraper.scrape_company(clean_website)
            
            if not scraped_data:
                print(f"[{competitor_id}] {name}: Failed to scrape")
                return False
            
            # Save to database
            success = self.db_ops.save_competitor(scraped_data)
            
            if success:
                print(f"[{competitor_id}] {name}: ✓ Successfully enriched")
            else:
                print(f"[{competitor_id}] {name}: ✗ Failed to save")
            
            return success
            
        except Exception as e:
            print(f"Error enriching competitor {competitor.get('id')}: {str(e)}")
            return False
    
    def enrich_all_competitors(self, limit: int = None, skip_existing: bool = False) -> Dict:
        """
        Enrich all competitors in database with parsers.vc data
        
        Args:
            limit: Maximum number of competitors to process (None = all)
            skip_existing: Skip competitors that already have data
            
        Returns:
            Dictionary with statistics
        """
        print("=" * 80)
        print("COMPETITOR ENRICHMENT SERVICE")
        print("=" * 80)
        
        # Get all competitors
        competitors = self.db_ops.get_all_competitors_for_enrichment()
        
        if not competitors:
            print("No competitors found in database")
            return {'total': 0, 'processed': 0, 'successful': 0, 'failed': 0}
        
        # Apply limit if specified
        if limit:
            competitors = competitors[:limit]
        
        total = len(competitors)
        processed = 0
        successful = 0
        failed = 0
        
        print(f"\nFound {total} competitors to enrich")
        print("-" * 80)
        
        for i, competitor in enumerate(competitors, 1):
            print(f"\nProgress: {i}/{total}")
            
            # Process competitor
            success = self.enrich_competitor(competitor)
            
            processed += 1
            if success:
                successful += 1
            else:
                failed += 1
            
            # Delay between requests (except for last one)
            if i < total:
                print(f"Waiting {self.delay}s before next request...")
                time.sleep(self.delay)
        
        # Print summary
        print("\n" + "=" * 80)
        print("ENRICHMENT SUMMARY")
        print("=" * 80)
        print(f"Total competitors: {total}")
        print(f"Processed: {processed}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Success rate: {(successful/processed*100):.1f}%")
        print("=" * 80)
        
        return {
            'total': total,
            'processed': processed,
            'successful': successful,
            'failed': failed
        }


def main():
    """Main function to run enrichment service"""
    # Initialize database
    db = get_db()
    db.initialize()
    
    # Create enrichment service
    service = CompetitorEnrichmentService(
        headless=True,
        delay_between_requests=2.0
    )
    
    # Enrich all competitors (or set limit for testing)
    results = service.enrich_all_competitors(limit=None)
    
    print("\nEnrichment complete!")


if __name__ == "__main__":
    main()

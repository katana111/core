"""
Database operations for saving Tracxn scraped data to competitors table
"""

from typing import Dict, Optional, List
from datetime import datetime
from mysql.connector import Error
import sys
import os

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from database import get_db


class CompetitorDB:
    """Handle database operations for competitors table"""
    
    def __init__(self):
        """
        Initialize competitor database operations
        Uses centralized database connection via dependency injection
        """
        self.db = get_db()
    
    def _map_scraped_data_to_competitor(self, scraped_data: Dict) -> Dict:
        """
        Map scraped company data to competitors table structure
        
        Args:
            scraped_data: Dictionary from TracxnScraper
            
        Returns:
            Dictionary with competitors table fields
        """
        import re
        
        # Extract company name and derive website if not available
        company_name = scraped_data.get('company_name', '')
        website = scraped_data.get('website', '')
        
        # Hardcoded website mapping for known companies
        if not website and 'SEON' in company_name:
            website = 'seon.io'
        
        # Convert funding amount to numeric (e.g., "$187M" -> 187000000)
        funding_str = scraped_data.get('fundings', {}).get('total_funding', '')
        fundings_total = None
        if funding_str:
            # Remove $ and convert M/B/K to numbers
            match = re.search(r'\$?([\d.]+)([MBK]?)', funding_str, re.IGNORECASE)
            if match:
                amount = float(match.group(1))
                unit = match.group(2).upper()
                
                if unit == 'B':
                    fundings_total = amount * 1000000000
                elif unit == 'M':
                    fundings_total = amount * 1000000
                elif unit == 'K':
                    fundings_total = amount * 1000
                else:
                    fundings_total = amount
        
        competitor = {
            'name': company_name,
            'website': website or None,
            'address': scraped_data.get('registered_address') or scraped_data.get('main_office') or scraped_data.get('location', ''),
            'email': None,  # Not available from Tracxn scraper - use NULL for empty
            'pricing': None,  # Not available from Tracxn scraper - use NULL for JSON columns
            'founded_year': scraped_data.get('founded_year', '') or None,
            'funding_stage': scraped_data.get('funding_stage', '') or None,
            'fundings_total': fundings_total,
            'employee_qty': scraped_data.get('employee_count', '') or None,
            'founders': None,  # Not available from Tracxn scraper - use NULL for empty
            'score': 0  # Default score
        }
        
        return competitor
    
    def _competitor_exists(self, cursor, name: str) -> Optional[int]:
        """
        Check if competitor with given name already exists
        
        Args:
            cursor: Database cursor
            name: Company name
            
        Returns:
            Competitor ID if exists, None otherwise
        """
        try:
            query = "SELECT id FROM competitors WHERE name = %s LIMIT 1"
            cursor.execute(query, (name,))
            result = cursor.fetchone()
            if result:
                return result[0]
        except Error as e:
            print(f"Error checking competitor existence: {e}")
        
        return None
    
    def insert_competitor(self, competitor_data: Dict) -> Optional[int]:
        """
        Insert new competitor into database
        
        Args:
            competitor_data: Mapped competitor data
            
        Returns:
            Inserted record ID or None if failed
        """
        try:
            with self.db.get_cursor() as cursor:
                query = """
                    INSERT INTO competitors 
                    (name, website, address, email, pricing, founded_year, 
                     funding_stage, fundings_total, employee_qty, founders, score, 
                     created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                """
                
                values = (
                    competitor_data.get('name', ''),
                    competitor_data.get('website') or 'unknown.com',  # Fallback for required field
                    competitor_data.get('address', '') or None,
                    competitor_data.get('email'),
                    competitor_data.get('pricing'),
                    competitor_data.get('founded_year'),
                    competitor_data.get('funding_stage'),
                    competitor_data.get('fundings_total'),
                    competitor_data.get('employee_qty'),
                    competitor_data.get('founders'),
                    competitor_data.get('score', 0)
                )
                
                cursor.execute(query, values)
                inserted_id = cursor.lastrowid
                print(f"✅ Inserted new competitor: {competitor_data.get('name')} (ID: {inserted_id})")
                return inserted_id
            
        except Error as e:
            print(f"❌ Error inserting competitor: {e}")
            return None
    
    def update_competitor(self, competitor_id: int, competitor_data: Dict) -> bool:
        """
        Update existing competitor in database
        
        Args:
            competitor_id: ID of competitor to update
            competitor_data: Mapped competitor data
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            with self.db.get_cursor() as cursor:
                query = """
                    UPDATE competitors 
                    SET address = %s, 
                        email = %s, 
                        pricing = %s, 
                        founded_year = %s,
                        funding_stage = %s, 
                        fundings_total = %s, 
                        employee_qty = %s, 
                        founders = %s,
                        score = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """
                
                values = (
                    competitor_data.get('address', '') or None,
                    competitor_data.get('email'),
                    competitor_data.get('pricing'),
                    competitor_data.get('founded_year'),
                    competitor_data.get('funding_stage'),
                    competitor_data.get('fundings_total'),
                    competitor_data.get('employee_qty'),
                    competitor_data.get('founders'),
                    competitor_data.get('score', 0),
                    competitor_id
                )
                
                cursor.execute(query, values)
                print(f"✅ Updated competitor: {competitor_data.get('name')} (ID: {competitor_id})")
                return True
            
        except Error as e:
            print(f"❌ Error updating competitor: {e}")
            return False
    
    def save_competitor(self, scraped_data: Dict) -> Optional[int]:
        """
        Save or update competitor from scraped data
        If competitor with same name exists, update it; otherwise insert new
        
        Args:
            scraped_data: Raw data from TracxnScraper
            
        Returns:
            Competitor ID (new or existing) or None if failed
        """
        # Map scraped data to competitor table structure
        competitor_data = self._map_scraped_data_to_competitor(scraped_data)
        
        # Check if competitor name is valid
        name = competitor_data.get('name', '').strip()
        if not name:
            print("❌ Cannot save competitor without name")
            return None
        
        try:
            with self.db.get_cursor() as cursor:
                # Check if competitor exists
                existing_id = self._competitor_exists(cursor, name)
            
            if existing_id:
                # Update existing competitor
                print(f"Competitor '{name}' already exists (ID: {existing_id}), updating...")
                success = self.update_competitor(existing_id, competitor_data)
                return existing_id if success else None
            else:
                # Insert new competitor
                print(f"Inserting new competitor: {name}")
                return self.insert_competitor(competitor_data)
                
        except Error as e:
            print(f"❌ Error in save_competitor: {e}")
            return None
    
    def save_competitors_batch(self, scraped_data_list: List[Dict]) -> Dict:
        """
        Save multiple competitors from scraped data
        
        Args:
            scraped_data_list: List of scraped company data
            
        Returns:
            Dictionary with statistics (inserted, updated, failed)
        """
        stats = {
            'inserted': 0,
            'updated': 0,
            'failed': 0,
            'total': len(scraped_data_list)
        }
        
        for i, scraped_data in enumerate(scraped_data_list, 1):
            print(f"\n{'='*60}")
            print(f"Processing competitor {i}/{stats['total']}")
            print(f"{'='*60}")
            
            try:
                # Map data
                competitor_data = self._map_scraped_data_to_competitor(scraped_data)
                name = competitor_data.get('name', '').strip()
                
                if not name:
                    print("❌ Skipping: No company name")
                    stats['failed'] += 1
                    continue
                
                # Check if exists
                connection = self.db_config.get_connection()
                cursor = connection.cursor()
                existing_id = self._competitor_exists(cursor, name)
                cursor.close()
                
                if existing_id:
                    # Update
                    success = self.update_competitor(existing_id, competitor_data)
                    if success:
                        stats['updated'] += 1
                    else:
                        stats['failed'] += 1
                else:
                    # Insert
                    new_id = self.insert_competitor(competitor_data)
                    if new_id:
                        stats['inserted'] += 1
                    else:
                        stats['failed'] += 1
                        
            except Exception as e:
                print(f"❌ Error processing competitor: {e}")
                stats['failed'] += 1
        
        # Print summary
        print(f"\n{'='*60}")
        print("BATCH PROCESSING SUMMARY")
        print(f"{'='*60}")
        print(f"Total: {stats['total']}")
        print(f"✅ Inserted: {stats['inserted']}")
        print(f"🔄 Updated: {stats['updated']}")
        print(f"❌ Failed: {stats['failed']}")
        print(f"{'='*60}\n")
        
        return stats
    
    def get_competitor_by_name(self, name: str) -> Optional[Dict]:
        """
        Retrieve competitor by name
        
        Args:
            name: Company name
            
        Returns:
            Competitor data dictionary or None
        """
        try:
            with self.db.get_cursor(dictionary=True) as cursor:
                query = "SELECT * FROM competitors WHERE name = %s LIMIT 1"
                cursor.execute(query, (name,))
                return cursor.fetchone()
        except Error as e:
            print(f"Error retrieving competitor: {e}")
            return None

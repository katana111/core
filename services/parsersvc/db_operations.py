"""
Database operations for Parsers.vc scraped data
Maps parsers.vc data to competitors table with comparison logic
"""

import json
from typing import Dict, Optional, List
from datetime import datetime
from dateutil import parser as date_parser
from database import get_db
from services.ai.news_analyzer import NewsAnalyzer


class ParsersVCDataOperations:
    """Handle database operations for Parsers.vc scraped data"""
    
    def __init__(self, analyze_news: bool = True):
        """
        Initialize with centralized database connection
        
        Args:
            analyze_news: Whether to use AI to analyze press mentions
        """
        self.db = get_db()
        self.news_analyzer = NewsAnalyzer() if analyze_news else None
    
    def _convert_funding_to_numeric(self, funding_str: Optional[float]) -> Optional[float]:
        """
        Convert funding amount to numeric value
        
        Args:
            funding_str: Numeric funding value (already converted by scraper)
            
        Returns:
            Float value or None
        """
        if funding_str is None:
            return None
        
        try:
            return float(funding_str)
        except (ValueError, TypeError):
            return None
    
    def _parse_employee_range(self, employee_str: str) -> Optional[int]:
        """
        Parse employee count from string (e.g., "50-100" -> 75)
        Takes the midpoint of range
        
        Args:
            employee_str: Employee count string
            
        Returns:
            Integer employee count or None
        """
        if not employee_str:
            return None
        
        try:
            # Handle ranges like "50-100"
            if '-' in employee_str:
                parts = employee_str.split('-')
                low = int(parts[0].strip())
                high = int(parts[1].strip())
                return (low + high) // 2
            else:
                # Single number
                return int(employee_str.strip())
        except (ValueError, IndexError):
            return None
    
    def _get_existing_competitor(self, website: str) -> Optional[Dict]:
        """
        Find existing competitor by website (matches cleaned URLs)
        
        Args:
            website: Company website (cleaned, e.g., 'seon.io')
            
        Returns:
            Dictionary with competitor data or None
        """
        # Try multiple matching strategies
        queries = [
            # Exact match
            ("SELECT id, name, website, address, email, pricing, founded_year, "
             "funding_stage, fundings_total, employee_qty, founders, score, "
             "created_at, updated_at FROM competitors WHERE website = %s LIMIT 1", 
             (website,)),
            # Match with https://
            ("SELECT id, name, website, address, email, pricing, founded_year, "
             "funding_stage, fundings_total, employee_qty, founders, score, "
             "created_at, updated_at FROM competitors WHERE website = %s LIMIT 1", 
             (f'https://{website}',)),
            # Match with http://
            ("SELECT id, name, website, address, email, pricing, founded_year, "
             "funding_stage, fundings_total, employee_qty, founders, score, "
             "created_at, updated_at FROM competitors WHERE website = %s LIMIT 1", 
             (f'http://{website}',)),
            # Match with https://www.
            ("SELECT id, name, website, address, email, pricing, founded_year, "
             "funding_stage, fundings_total, employee_qty, founders, score, "
             "created_at, updated_at FROM competitors WHERE website = %s LIMIT 1", 
             (f'https://www.{website}',)),
            # Match with www.
            ("SELECT id, name, website, address, email, pricing, founded_year, "
             "funding_stage, fundings_total, employee_qty, founders, score, "
             "created_at, updated_at FROM competitors WHERE website = %s LIMIT 1", 
             (f'www.{website}',)),
            # Partial match (LIKE with %)
            ("SELECT id, name, website, address, email, pricing, founded_year, "
             "funding_stage, fundings_total, employee_qty, founders, score, "
             "created_at, updated_at FROM competitors WHERE website LIKE %s LIMIT 1", 
             (f'%{website}%',)),
        ]
        
        with self.db.get_cursor() as cursor:
            for query, params in queries:
                cursor.execute(query, params)
                row = cursor.fetchone()
                
                if row:
                    return {
                        'id': row[0],
                        'name': row[1],
                        'website': row[2],
                        'address': row[3],
                        'email': row[4],
                        'pricing': row[5],
                        'founded_year': row[6],
                        'funding_stage': row[7],
                        'fundings_total': row[8],
                        'employee_qty': row[9],
                        'founders': row[10],
                        'score': row[11],
                        'created_at': row[12],
                        'updated_at': row[13]
                    }
        return None
    
    def _map_scraped_to_competitor(self, scraped_data: Dict, existing: Optional[Dict] = None) -> Dict:
        """
        Map parsers.vc scraped data to competitors table format
        Compares total raised with existing value and keeps higher
        
        Args:
            scraped_data: Data from parsers.vc scraper
            existing: Existing competitor record (if any)
            
        Returns:
            Dictionary ready for database insertion/update
        """
        competitor_data = {}
        
        # Location -> address
        if scraped_data.get('location'):
            competitor_data['address'] = scraped_data['location']
        
        # Employees
        employee_qty = self._parse_employee_range(scraped_data.get('employees', ''))
        if employee_qty is not None:
            competitor_data['employee_qty'] = employee_qty
        
        # Founded year
        if scraped_data.get('founded_year'):
            competitor_data['founded_year'] = int(scraped_data['founded_year'])
        
        # Categories
        if scraped_data.get('categories'):
            import json
            competitor_data['categories'] = json.dumps(scraped_data['categories'])
        
        # Total raised - compare with existing and keep higher value
        new_funding = self._convert_funding_to_numeric(scraped_data.get('total_raised'))
        existing_funding = existing.get('fundings_total') if existing else None
        
        # Convert existing_funding to float for comparison
        if existing_funding is not None:
            try:
                existing_funding = float(existing_funding)
            except (ValueError, TypeError):
                existing_funding = None
        
        if new_funding is not None and existing_funding is not None:
            # Keep higher value
            competitor_data['fundings_total'] = max(new_funding, existing_funding)
            print(f"Funding comparison - New: ${new_funding:,.0f}, Existing: ${existing_funding:,.0f}, "
                  f"Keeping: ${competitor_data['fundings_total']:,.0f}")
        elif new_funding is not None:
            # Only new value available
            competitor_data['fundings_total'] = new_funding
        elif existing_funding is not None:
            # Only existing value available (keep as is)
            pass
        
        # Update timestamp
        competitor_data['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return competitor_data
    
    def save_competitor(self, scraped_data: Dict) -> bool:
        """
        Save or update competitor data from parsers.vc
        
        Args:
            scraped_data: Data from parsers.vc scraper
            
        Returns:
            True if successful, False otherwise
        """
        if not scraped_data or not scraped_data.get('website'):
            print("Error: Invalid scraped data")
            return False
        
        try:
            website = scraped_data['website']
            
            # Check if competitor exists
            existing = self._get_existing_competitor(website)
            
            if not existing:
                print(f"Warning: No existing competitor found for {website}")
                print("Parsers.vc scraper is designed to enrich existing records")
                return False
            
            # Map data with comparison logic
            competitor_data = self._map_scraped_to_competitor(scraped_data, existing)
            
            # Update competitor record
            success = False
            if competitor_data:
                success = self._update_competitor(existing['id'], competitor_data)
            
            # Process press mentions with AI analysis
            if scraped_data.get('press_mentions'):
                self._save_press_mentions(
                    existing['id'], 
                    existing['name'],
                    scraped_data['press_mentions']
                )
            
            return success or bool(scraped_data.get('press_mentions'))
        
        except Exception as e:
            print(f"Error saving competitor: {str(e)}")
            return False
    
    def _update_competitor(self, competitor_id: int, data: Dict) -> bool:
        """
        Update existing competitor record
        
        Args:
            competitor_id: ID of competitor to update
            data: Dictionary with fields to update
            
        Returns:
            True if successful
        """
        if not data:
            return False
        
        # Build UPDATE query dynamically (exclude website and name to prevent overriding)
        fields = []
        values = []
        
        for key, value in data.items():
            if key not in ('website', 'name'):  # Never update website or name
                fields.append(f"{key} = %s")
                values.append(value)
        
        if not fields:
            print(f"No fields to update for competitor ID {competitor_id}")
            return False
        
        values.append(competitor_id)
        
        query = f"""
            UPDATE competitors
            SET {', '.join(fields)}
            WHERE id = %s
        """
        
        with self.db.get_cursor() as cursor:
            cursor.execute(query, tuple(values))
            affected = cursor.rowcount
            
            if affected > 0:
                print(f"Updated competitor ID {competitor_id}")
                return True
            else:
                print(f"No rows updated for competitor ID {competitor_id}")
                return False
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """
        Parse various date formats to MySQL DATE format
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            Date in YYYY-MM-DD format or None
        """
        if not date_str:
            return None
        
        try:
            parsed_date = date_parser.parse(date_str, fuzzy=True)
            return parsed_date.strftime('%Y-%m-%d')
        except:
            return None
    
    def _save_press_mentions(self, competitor_id: int, company_name: str, mentions: List[Dict]):
        """
        Save press mentions with AI analysis to competitors_news table
        
        Args:
            competitor_id: ID of the competitor
            company_name: Name of the company
            mentions: List of press mention dictionaries
        """
        if not mentions:
            return
        
        print(f"Analyzing {len(mentions)} press mentions with AI...")
        
        for mention in mentions:
            try:
                title = mention.get('title', '')[:255]
                content = mention.get('content', '')
                
                # Analyze with AI
                if self.news_analyzer:
                    analysis_result = self.news_analyzer.analyze_article(
                        title,
                        content,
                        company_name
                    )
                    
                    # Check if article is relevant for business intelligence
                    if not analysis_result.get('relevant', True):
                        print(f"    ⚠ Skipped press mention (not business-relevant: {analysis_result.get('reason', 'Unknown')})")
                        continue
                    
                    # Use AI-cleaned title and main idea
                    cleaned_title = analysis_result.get('title', title)[:255]
                    main_idea = analysis_result.get('main_idea', content)
                    sentiment = analysis_result.get('sentiment', 'neutral')
                    sentiment_score = analysis_result.get('sentiment_score', 0.0)
                    analysis_text = analysis_result.get('analysis', '')
                    
                    # Calculate importance grade (1-10) based on sentiment score
                    importance_grade = min(10, max(1, int(abs(sentiment_score) * 10)))
                else:
                    # Fallback without AI
                    cleaned_title = title
                    main_idea = content
                    sentiment = 'neutral'
                    sentiment_score = 0.0
                    analysis_text = f"Press mention: {title}"
                    importance_grade = 5
                
                # Parse date
                published_date = self._parse_date(mention.get('date', ''))
                if not published_date:
                    published_date = datetime.now().strftime('%Y-%m-%d')
                
                # Check if this news already exists (avoid duplicates)
                with self.db.get_cursor() as cursor:
                    cursor.execute("""
                        SELECT id FROM competitors_news 
                        WHERE competitor_id = %s AND title = %s
                        LIMIT 1
                    """, (competitor_id, cleaned_title))
                    
                    exists = cursor.fetchone()
                    
                    if exists:
                        continue  # Skip duplicate
                    
                    # Combine main_idea and analysis for the analysis field
                    full_analysis = f"{main_idea}\n\n{analysis_text}"
                    
                    # Insert news with analysis - match existing schema
                    query = """
                        INSERT INTO competitors_news 
                        (competitor_id, title, date, link, analysis, importance_grade, sentiment)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """
                    
                    values = (
                        competitor_id,
                        cleaned_title,
                        published_date,
                        mention.get('url', ''),
                        full_analysis,
                        importance_grade,
                        sentiment
                    )
                    
                    cursor.execute(query, values)
                    print(f"  ✓ Saved: {cleaned_title[:80]}... (Sentiment: {sentiment}, Grade: {importance_grade})")
            
            except Exception as e:
                print(f"  ✗ Error saving press mention: {str(e)}")
                continue
    
    def get_all_competitors_for_enrichment(self):
        """
        Get all competitors that need enrichment from parsers.vc
        
        Returns:
            List of dictionaries with id, name, website
        """
        query = """
            SELECT id, name, website
            FROM competitors
            WHERE website IS NOT NULL AND website != ''
            ORDER BY id
        """
        
        with self.db.get_cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            
            competitors = []
            for row in rows:
                competitors.append({
                    'id': row[0],
                    'name': row[1],
                    'website': row[2]
                })
            
            return competitors

"""
Database operations for BiometricUpdate news data
Saves scraped articles to competitors_news table with AI analysis
"""

import json
from typing import Dict, List, Optional
from datetime import datetime
from dateutil import parser as date_parser
from database import get_db
from services.ai.news_analyzer import NewsAnalyzer


class BiometricUpdateDataOperations:
    """Handle database operations for BiometricUpdate scraped news"""
    
    def __init__(self, analyze_news: bool = True):
        """
        Initialize with centralized database connection
        
        Args:
            analyze_news: Whether to use AI to analyze articles
        """
        self.db = get_db()
        self.news_analyzer = NewsAnalyzer() if analyze_news else None
    
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
            return datetime.now().strftime('%Y-%m-%d')
    
    def _get_competitor_by_name(self, company_name: str) -> Optional[Dict]:
        """
        Find competitor by company name
        
        Args:
            company_name: Name of the company
            
        Returns:
            Dictionary with competitor data or None
        """
        # Try exact match first
        queries = [
            ("SELECT id, name FROM competitors WHERE name = %s LIMIT 1", (company_name,)),
            ("SELECT id, name FROM competitors WHERE name LIKE %s LIMIT 1", (f"%{company_name}%",)),
            ("SELECT id, name FROM competitors WHERE LOWER(name) LIKE LOWER(%s) LIMIT 1", (f"%{company_name}%",)),
        ]
        
        with self.db.get_cursor() as cursor:
            for query, params in queries:
                cursor.execute(query, params)
                row = cursor.fetchone()
                
                if row:
                    return {
                        'id': row[0],
                        'name': row[1]
                    }
        
        return None
    
    def _save_article(self, competitor_id: int, company_name: str, article: Dict) -> bool:
        """
        Save a single article to competitors_news table
        
        Args:
            competitor_id: ID of the competitor
            company_name: Name of the company
            article: Article data dictionary
            
        Returns:
            True if successful
        """
        try:
            title = article.get('title', '')[:255]
            content = article.get('content', '')
            url = article.get('url', '')
            
            # Analyze with AI
            if self.news_analyzer and content:
                analysis_result = self.news_analyzer.analyze_article(
                    title,
                    content,
                    company_name
                )
                
                # Check if article is relevant for business intelligence
                if not analysis_result.get('relevant', True):
                    print(f"    ⚠ Skipped (not business-relevant: {analysis_result.get('reason', 'Unknown')})")
                    return False
                
                # Use AI results
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
                main_idea = content[:500] + "..." if len(content) > 500 else content
                sentiment = 'neutral'
                analysis_text = f"BiometricUpdate article about {company_name}"
                importance_grade = 5
            
            # Parse date
            published_date = self._parse_date(article.get('date', ''))
            
            # Check if this article already exists (avoid duplicates)
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT id FROM competitors_news 
                    WHERE competitor_id = %s AND (title = %s OR link = %s)
                    LIMIT 1
                """, (competitor_id, cleaned_title, url))
                
                exists = cursor.fetchone()
                
                if exists:
                    return False  # Skip duplicate
                
                # Combine main_idea and analysis for the analysis field
                full_analysis = f"{main_idea}\n\n{analysis_text}"
                
                # Insert article into competitors_news table
                query = """
                    INSERT INTO competitors_news 
                    (competitor_id, title, date, link, analysis, importance_grade, sentiment)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                
                values = (
                    competitor_id,
                    cleaned_title,
                    published_date,
                    url,
                    full_analysis,
                    importance_grade,
                    sentiment
                )
                
                cursor.execute(query, values)
                return True
                
        except Exception as e:
            print(f"Error saving article: {str(e)}")
            return False
    
    def save_company_articles(self, company_name: str, articles: List[Dict]) -> Dict:
        """
        Save articles for a company to the database
        
        Args:
            company_name: Name of the company
            articles: List of article dictionaries
            
        Returns:
            Dictionary with statistics
        """
        if not articles:
            return {'total': 0, 'saved': 0, 'skipped': 0, 'error': 'No articles provided'}
        
        # Find the competitor in database
        competitor = self._get_competitor_by_name(company_name)
        
        if not competitor:
            return {
                'total': len(articles), 
                'saved': 0, 
                'skipped': len(articles),
                'error': f'Competitor "{company_name}" not found in database'
            }
        
        competitor_id = competitor['id']
        competitor_name = competitor['name']
        
        print(f"Saving {len(articles)} articles for {competitor_name} (ID: {competitor_id})")
        
        saved = 0
        skipped = 0
        
        for i, article in enumerate(articles, 1):
            print(f"  [{i}/{len(articles)}] Processing: {article.get('title', 'Unknown')[:60]}...")
            
            success = self._save_article(competitor_id, competitor_name, article)
            
            if success:
                saved += 1
                print(f"    ✓ Saved")
            else:
                skipped += 1
                print(f"    ⚠ Skipped (duplicate or error)")
        
        return {
            'total': len(articles),
            'saved': saved,
            'skipped': skipped,
            'competitor_id': competitor_id,
            'competitor_name': competitor_name
        }
    
    def get_all_competitor_names(self) -> List[str]:
        """
        Get all competitor names for batch processing
        
        Returns:
            List of competitor names
        """
        query = "SELECT DISTINCT name FROM competitors WHERE name IS NOT NULL ORDER BY name"
        
        with self.db.get_cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            
            return [row[0] for row in rows]
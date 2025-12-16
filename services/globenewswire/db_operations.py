"""
Database operations for GlobeNewswire news articles.
Handles saving scraped articles to the database with AI analysis integration.
"""

from typing import List, Dict, Optional
from database import get_db
from services.ai.news_analyzer import NewsAnalyzer


class GlobeNewswireDataOperations:
    """Handle database operations for GlobeNewswire news data"""
    
    def __init__(self, analyze_news: bool = True):
        """
        Initialize database operations
        
        Args:
            analyze_news: Whether to use AI analysis for news articles
        """
        self.db = get_db()
        self.analyze_news = analyze_news
        self.analyzer = NewsAnalyzer() if analyze_news else None
    
    def get_competitor_by_name(self, name: str) -> Optional[Dict]:
        """
        Get competitor information by name
        
        Args:
            name: Competitor name to search for
            
        Returns:
            Competitor data dictionary or None if not found
        """
        query = """
        SELECT id, name, website 
        FROM competitors 
        WHERE LOWER(name) = LOWER(%s)
        LIMIT 1
        """
        
        with self.db.get_cursor() as cursor:
            cursor.execute(query, (name,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': row[0],
                    'name': row[1], 
                    'website': row[2]
                }
        
        return None
    
    def get_all_competitors(self) -> List[Dict]:
        """
        Get all competitors from database
        
        Returns:
            List of competitor dictionaries
        """
        query = """
        SELECT id, name, website 
        FROM competitors 
        ORDER BY name
        """
        
        competitors = []
        with self.db.get_cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            
            if rows:
                for row in rows:
                    competitors.append({
                        'id': row[0],
                        'name': row[1],
                        'website': row[2]
                    })
        
        return competitors
    
    def _article_exists(self, competitor_id: int, title: str, url: str) -> bool:
        """
        Check if article already exists in database
        
        Args:
            competitor_id: ID of the competitor
            title: Article title
            url: Article URL
            
        Returns:
            True if article exists, False otherwise
        """
        query = """
        SELECT COUNT(*) FROM competitors_news 
        WHERE competitor_id = %s 
        AND (title = %s OR link = %s)
        """
        
        with self.db.get_cursor() as cursor:
            cursor.execute(query, (competitor_id, title, url))
            row = cursor.fetchone()
            return row and row[0] > 0
    
    def _save_article(self, competitor_id: int, article_data: Dict) -> bool:
        """
        Save a single article to the database with AI analysis
        
        Args:
            competitor_id: ID of the competitor
            article_data: Article data dictionary
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Check for duplicates
            if self._article_exists(competitor_id, article_data.get('title', ''), article_data.get('url', '')):
                print(f"⚠️  Article already exists: {article_data.get('title', 'Unknown')}")
                return False
            
            # Analyze article with AI if enabled
            if self.analyzer:
                company_name = article_data.get('competitor_name', article_data.get('target_company', 'Unknown'))
                print(f"🤖 Analyzing article with AI: {article_data.get('title', '')[:50]}...")
                
                analysis = self.analyzer.analyze_article(
                    article_data.get('title', ''),
                    article_data.get('content', ''),
                    company_name
                )
                
                # Check if article is business-relevant
                if not analysis.get('relevant', True):
                    print(f"📰 Skipping non-business article: {analysis.get('reason', 'not business relevant')}")
                    return False
                
                # Create company-specific title
                company_focused_title = analysis.get('title', article_data.get('title', ''))
                if company_focused_title == article_data.get('title', '') and company_name.lower() in company_focused_title.lower():
                    # Title already mentions company, keep as is
                    final_title = company_focused_title
                elif company_name != 'Unknown' and company_name.lower() not in company_focused_title.lower():
                    # Add company context to title if not present
                    final_title = f"{company_name}: {company_focused_title}"
                else:
                    final_title = company_focused_title
                
                # Create company-focused analysis
                main_idea = analysis.get('main_idea', 'No summary available')
                company_analysis = analysis.get('analysis', '')
                
                # Filter analysis to focus on the target company
                if company_name != 'Unknown':
                    company_focused_analysis = f"Impact on {company_name}: {company_analysis}\n\nKey Details: {main_idea}"
                else:
                    company_focused_analysis = f"{main_idea}\n\nAnalysis: {company_analysis}"
                
                sentiment = analysis.get('sentiment', 'neutral')
                
                # Convert business impact to importance grade
                business_impact = analysis.get('business_impact', 'medium')
                if business_impact == 'high':
                    importance = 5
                elif business_impact == 'medium':
                    importance = 3
                else:
                    importance = 1
            else:
                company_name = article_data.get('competitor_name', article_data.get('target_company', 'Unknown'))
                original_title = article_data.get('title', '')
                
                # Create company-specific title without AI
                if company_name != 'Unknown' and company_name.lower() not in original_title.lower():
                    final_title = f"{company_name}: {original_title}"
                else:
                    final_title = original_title
                    
                company_focused_analysis = f"Article about {company_name}: {original_title}"
                sentiment = 'neutral'
                importance = 3
            
            # Insert article into database using the actual schema
            query = """
            INSERT INTO competitors_news (
                competitor_id, title, link, analysis, importance_grade, sentiment, date, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
            )
            """
            
            # Parse published date or use current date
            published_date = article_data.get('published_date')
            if published_date:
                # Try to convert to proper timestamp
                try:
                    from datetime import datetime
                    if isinstance(published_date, str):
                        # Try parsing the date string
                        import dateutil.parser
                        parsed_date = dateutil.parser.parse(published_date)
                        published_date = parsed_date.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    published_date = None
            
            if not published_date:
                published_date = 'NOW()'
                values = (
                    competitor_id,
                    final_title,
                    article_data.get('url', ''),
                    company_focused_analysis,
                    importance,
                    sentiment
                )
                query = """
                INSERT INTO competitors_news (
                    competitor_id, title, link, analysis, importance_grade, sentiment, date, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW()
                )
                """
            else:
                values = (
                    competitor_id,
                    final_title,
                    article_data.get('url', ''),
                    company_focused_analysis,
                    importance,
                    sentiment,
                    published_date
                )
            
            with self.db.get_cursor() as cursor:
                cursor.execute(query, values)
            
            print(f"✅ Saved article: {final_title[:50]}...")
            return True
            
        except Exception as e:
            print(f"❌ Error saving article: {e}")
            return False
    
    def save_competitor_news(self, competitor_name: str, articles: List[Dict]) -> Dict:
        """
        Save competitor news articles to database
        
        Args:
            competitor_name: Name of the competitor
            articles: List of article data dictionaries
            
        Returns:
            Dictionary with save statistics
        """
        # Get competitor info
        competitor = self.get_competitor_by_name(competitor_name)
        if not competitor:
            return {
                'success': False,
                'message': f'Competitor {competitor_name} not found in database',
                'saved_count': 0,
                'total_count': len(articles)
            }
        
        print(f"💾 Saving {len(articles)} GlobeNewswire articles for {competitor_name}...")
        
        saved_count = 0
        for article in articles:
            # Add competitor context to article data
            article['competitor_name'] = competitor_name
            if self._save_article(competitor['id'], article):
                saved_count += 1
        
        success_rate = (saved_count / len(articles) * 100) if articles else 0
        
        result = {
            'success': True,
            'message': f'Saved {saved_count}/{len(articles)} articles for {competitor_name}',
            'saved_count': saved_count,
            'total_count': len(articles),
            'success_rate': success_rate,
            'competitor_id': competitor['id']
        }
        
        print(f"📊 GlobeNewswire save results: {result['message']} ({success_rate:.1f}% success rate)")
        
        return result
    
    def get_recent_news(self, competitor_name: str = None, days: int = 30, limit: int = 10) -> List[Dict]:
        """
        Get recent news articles from database
        
        Args:
            competitor_name: Optional competitor name to filter by
            days: Number of days to look back
            limit: Maximum number of articles to return
            
        Returns:
            List of article dictionaries
        """
        if competitor_name:
            query = """
            SELECT cn.title, cn.link, cn.analysis, cn.date, cn.sentiment, c.name as company_name
            FROM competitors_news cn
            JOIN competitors c ON cn.competitor_id = c.id
            WHERE LOWER(c.name) = LOWER(%s)
            AND cn.created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            ORDER BY cn.date DESC, cn.created_at DESC
            LIMIT %s
            """
            values = (competitor_name, days, limit)
        else:
            query = """
            SELECT cn.title, cn.link, cn.analysis, cn.date, cn.sentiment, c.name as company_name
            FROM competitors_news cn
            JOIN competitors c ON cn.competitor_id = c.id
            WHERE cn.created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            ORDER BY cn.date DESC, cn.created_at DESC
            LIMIT %s
            """
            values = (days, limit)
        
        articles = []
        with self.db.get_cursor() as cursor:
            cursor.execute(query, values)
            rows = cursor.fetchall()
            
            if rows:
                for row in rows:
                    articles.append({
                        'title': row[0],
                        'link': row[1],
                        'analysis': row[2],
                        'date': row[3],
                        'sentiment': row[4],
                        'company_name': row[5]
                    })
        
        return articles
    
    def get_save_statistics(self, competitor_name: str = None) -> Dict:
        """
        Get statistics about saved GlobeNewswire articles
        
        Args:
            competitor_name: Optional competitor name to filter by
            
        Returns:
            Dictionary with statistics
        """
        if competitor_name:
            query = """
            SELECT 
                COUNT(*) as total_articles,
                COUNT(DISTINCT competitor_id) as companies_covered,
                AVG(importance_grade) as avg_importance,
                SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END) as positive_articles,
                SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) as negative_articles,
                SUM(CASE WHEN sentiment = 'neutral' THEN 1 ELSE 0 END) as neutral_articles
            FROM competitors_news cn
            JOIN competitors c ON cn.competitor_id = c.id
            WHERE LOWER(c.name) = LOWER(%s)
            """
            values = (competitor_name,)
        else:
            query = """
            SELECT 
                COUNT(*) as total_articles,
                COUNT(DISTINCT competitor_id) as companies_covered,
                AVG(importance_grade) as avg_importance,
                SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END) as positive_articles,
                SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) as negative_articles,
                SUM(CASE WHEN sentiment = 'neutral' THEN 1 ELSE 0 END) as neutral_articles
            FROM competitors_news 
            """
            values = None
        
        with self.db.get_cursor() as cursor:
            if values:
                cursor.execute(query, values)
            else:
                cursor.execute(query)
            row = cursor.fetchone()
            
            if row:
                return {
                    'total_articles': row[0] or 0,
                    'companies_covered': row[1] or 0,
                    'avg_importance': round(row[2] or 0.0, 2),
                    'positive_articles': row[3] or 0,
                    'negative_articles': row[4] or 0,
                    'neutral_articles': row[5] or 0
                }
        
        return {
            'total_articles': 0,
            'companies_covered': 0, 
            'avg_importance': 0.0,
            'positive_articles': 0,
            'negative_articles': 0,
            'neutral_articles': 0
        }


# Example usage
if __name__ == "__main__":
    # Initialize database operations
    db_ops = GlobeNewswireDataOperations(analyze_news=True)
    
    # Get all competitors
    competitors = db_ops.get_all_competitors()
    print(f"Found {len(competitors)} competitors in database")
    
    # Get statistics
    stats = db_ops.get_save_statistics()
    print(f"GlobeNewswire articles in database: {stats['total_articles']}")
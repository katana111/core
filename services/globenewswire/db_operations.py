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
        AND (title = %s OR url = %s)
        AND source = 'globenewswire'
        """
        
        result = self.db.execute_query(query, (competitor_id, title, url))
        
        return result and result[0][0] > 0
    
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
            analysis_data = {}
            if self.analyzer:
                print(f"🤖 Analyzing article with AI: {article_data.get('title', '')[:50]}...")
                analysis = self.analyzer.analyze_news_article(
                    article_data.get('content', ''),
                    article_data.get('title', '')
                )
                
                # Check if article is business-relevant
                if not analysis.get('is_business_relevant', True):
                    print(f"📰 Skipping non-business article: {article_data.get('title', '')[:50]}...")
                    return False
                
                analysis_data = {
                    'summary': analysis.get('summary', ''),
                    'sentiment': analysis.get('sentiment', 'neutral'),
                    'key_topics': ', '.join(analysis.get('key_topics', [])),
                    'business_impact': analysis.get('business_impact', ''),
                    'confidence_score': analysis.get('confidence_score', 0.0)
                }
            
            # Insert article into database
            query = """
            INSERT INTO competitors_news (
                competitor_id, title, url, content, published_date, source,
                summary, sentiment, key_topics, business_impact, confidence_score,
                created_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
            )
            """
            
            values = (
                competitor_id,
                article_data.get('title', ''),
                article_data.get('url', ''),
                article_data.get('content', ''),
                article_data.get('published_date'),
                'globenewswire',
                analysis_data.get('summary', ''),
                analysis_data.get('sentiment', 'neutral'),
                analysis_data.get('key_topics', ''),
                analysis_data.get('business_impact', ''),
                analysis_data.get('confidence_score', 0.0)
            )
            
            self.db.execute_update(query, values)
            print(f"✅ Saved article: {article_data.get('title', '')[:50]}...")
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
            SELECT cn.title, cn.url, cn.content, cn.published_date, cn.source,
                   cn.summary, cn.sentiment, cn.key_topics, c.name as company_name
            FROM competitors_news cn
            JOIN competitors c ON cn.competitor_id = c.id
            WHERE LOWER(c.name) = LOWER(%s)
            AND cn.source = 'globenewswire'
            AND cn.created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            ORDER BY cn.published_date DESC, cn.created_at DESC
            LIMIT %s
            """
            values = (competitor_name, days, limit)
        else:
            query = """
            SELECT cn.title, cn.url, cn.content, cn.published_date, cn.source,
                   cn.summary, cn.sentiment, cn.key_topics, c.name as company_name
            FROM competitors_news cn
            JOIN competitors c ON cn.competitor_id = c.id
            WHERE cn.source = 'globenewswire'
            AND cn.created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            ORDER BY cn.published_date DESC, cn.created_at DESC
            LIMIT %s
            """
            values = (days, limit)
        
        result = self.db.execute_query(query, values)
        
        articles = []
        if result:
            for row in result:
                articles.append({
                    'title': row[0],
                    'url': row[1],
                    'content': row[2],
                    'published_date': row[3],
                    'source': row[4],
                    'summary': row[5],
                    'sentiment': row[6], 
                    'key_topics': row[7],
                    'company_name': row[8]
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
                AVG(confidence_score) as avg_confidence,
                SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END) as positive_articles,
                SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) as negative_articles,
                SUM(CASE WHEN sentiment = 'neutral' THEN 1 ELSE 0 END) as neutral_articles
            FROM competitors_news cn
            JOIN competitors c ON cn.competitor_id = c.id
            WHERE LOWER(c.name) = LOWER(%s) AND cn.source = 'globenewswire'
            """
            values = (competitor_name,)
        else:
            query = """
            SELECT 
                COUNT(*) as total_articles,
                COUNT(DISTINCT competitor_id) as companies_covered,
                AVG(confidence_score) as avg_confidence,
                SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END) as positive_articles,
                SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) as negative_articles,
                SUM(CASE WHEN sentiment = 'neutral' THEN 1 ELSE 0 END) as neutral_articles
            FROM competitors_news 
            WHERE source = 'globenewswire'
            """
            values = None
        
        result = self.db.execute_query(query, values)
        
        if result and result[0]:
            return {
                'total_articles': result[0][0] or 0,
                'companies_covered': result[0][1] or 0,
                'avg_confidence': round(result[0][2] or 0.0, 2),
                'positive_articles': result[0][3] or 0,
                'negative_articles': result[0][4] or 0,
                'neutral_articles': result[0][5] or 0
            }
        
        return {
            'total_articles': 0,
            'companies_covered': 0, 
            'avg_confidence': 0.0,
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
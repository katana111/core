"""
GlobeNewswire scraper for competitor news articles.
Scrapes news articles from globenewswire.com using keyword search.
"""

import asyncio
import re
from typing import List, Dict, Optional
from urllib.parse import quote
from datetime import datetime, timedelta
from playwright.async_api import async_playwright, Browser, Page


class GlobeNewswireScraper:
    """Scraper for GlobeNewswire news articles"""
    
    def __init__(self, headless: bool = True, delay_between_requests: float = 2.0):
        """
        Initialize the scraper
        
        Args:
            headless: Whether to run browser in headless mode
            delay_between_requests: Delay between requests in seconds
        """
        self.headless = headless
        self.delay = delay_between_requests
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close_browser()
    
    async def start_browser(self):
        """Start the Playwright browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.page = await self.browser.new_page()
    
    async def close_browser(self):
        """Close the browser and Playwright"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        return text
    
    def _is_recent_article(self, date_str: str, months_back: int = 3) -> bool:
        """
        Check if article is within the specified months from current date
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            months_back: Number of months to look back
            
        Returns:
            True if article is recent, False otherwise
        """
        if not date_str:
            return True  # Include articles without dates to be safe
        
        try:
            article_date = datetime.strptime(date_str, '%Y-%m-%d')
            cutoff_date = datetime.now() - timedelta(days=months_back * 30)  # Approximate months
            return article_date >= cutoff_date
        except:
            return True  # Include articles with unparseable dates to be safe
    
    def _extract_date(self, date_text: str) -> Optional[str]:
        """
        Extract and normalize date from GlobeNewswire date format
        
        Args:
            date_text: Raw date text like "December 09, 2025 06:01 ET"
            
        Returns:
            Normalized date string in YYYY-MM-DD format or None
        """
        if not date_text:
            return None
        
        try:
            # GlobeNewswire format: "December 09, 2025 06:01 ET"
            # Extract the date part before time
            date_part = date_text.split(' ET')[0].strip()
            
            # Remove time if present (HH:MM)
            date_part = re.sub(r'\s+\d{2}:\d{2}$', '', date_part)
            
            # Convert month names to numbers
            months = {
                'January': '01', 'February': '02', 'March': '03', 'April': '04',
                'May': '05', 'June': '06', 'July': '07', 'August': '08',
                'September': '09', 'October': '10', 'November': '11', 'December': '12'
            }
            
            # Parse format like "December 09, 2025"
            parts = date_part.replace(',', '').split()
            if len(parts) >= 3:
                month_name = parts[0]
                day = parts[1].zfill(2)
                year = parts[2]
                
                if month_name in months:
                    month = months[month_name]
                    return f"{year}-{month}-{day}"
            
            return None
        except Exception:
            return None
        """
        Extract and normalize date from GlobeNewswire date format
        
        Args:
            date_text: Raw date text like "December 09, 2025 06:01 ET"
            
        Returns:
            Normalized date string in YYYY-MM-DD format or None
        """
        if not date_text:
            return None
        
        try:
            # GlobeNewswire format: "December 09, 2025 06:01 ET"
            # Extract the date part before time
            date_part = date_text.split(' ET')[0].strip()
            
            # Remove time if present (HH:MM)
            date_part = re.sub(r'\s+\d{2}:\d{2}$', '', date_part)
            
            # Convert month names to numbers
            months = {
                'January': '01', 'February': '02', 'March': '03', 'April': '04',
                'May': '05', 'June': '06', 'July': '07', 'August': '08',
                'September': '09', 'October': '10', 'November': '11', 'December': '12'
            }
            
            # Parse format like "December 09, 2025"
            parts = date_part.replace(',', '').split()
            if len(parts) >= 3:
                month_name = parts[0]
                day = parts[1].zfill(2)
                year = parts[2]
                
                if month_name in months:
                    month = months[month_name]
                    return f"{year}-{month}-{day}"
            
            return None
        except Exception:
            return None
    
    async def search_company_news(self, company_name: str, max_articles: int = 10, months_back: int = 3) -> List[Dict]:
        """
        Search for company news on GlobeNewswire with pagination and date filtering
        
        Args:
            company_name: Name of the company to search for
            max_articles: Maximum number of articles to return
            months_back: Only include articles from last N months
            
        Returns:
            List of article dictionaries with title, url, content, date, etc.
        """
        if not self.page:
            raise RuntimeError("Browser not started. Use async context manager or call start_browser()")
        
        articles = []
        page_num = 1
        max_pages = 10  # Safety limit to prevent infinite loops
        
        try:
            print(f"🔍 Searching GlobeNewswire for: {company_name} (last {months_back} months)")
            
            while len(articles) < max_articles and page_num <= max_pages:
                # Construct search URL with page parameter
                if page_num == 1:
                    search_url = f"https://www.globenewswire.com/search/keyword/{quote(company_name)}"
                else:
                    search_url = f"https://www.globenewswire.com/search/keyword/{quote(company_name)}/load/more?page={page_num}&pageSize=10"
                
                print(f"🌐 Fetching page {page_num}: {search_url}")
                
                # Navigate to search results
                await self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(self.delay)
                
                # Wait for search results to load
                try:
                    if page_num == 1:
                        await self.page.wait_for_selector('a[href*="/news-release/"]', timeout=10000)
                    else:
                        # For pagination, wait a bit longer as content loads dynamically
                        await asyncio.sleep(2)
                except:
                    print(f"⚠️  No search results found on page {page_num}")
                    break
                
                # Extract article links and basic info from search results
                article_elements = await self.page.query_selector_all('a[href*="/news-release/"]')
                
                if not article_elements:
                    print(f"📄 No more articles found on page {page_num}")
                    break
                
                print(f"📰 Found {len(article_elements)} potential articles on page {page_num}")
                
                # Track articles found on this page to detect when to stop
                page_articles_processed = 0
                articles_found_on_page = 0
                
                # Process each article on this page
                for element in article_elements:
                    if len(articles) >= max_articles:
                        break
                    
                    try:
                        # Get article URL
                        article_url = await element.get_attribute('href')
                        if not article_url or not article_url.startswith('http'):
                            if article_url and article_url.startswith('/'):
                                article_url = f"https://www.globenewswire.com{article_url}"
                            else:
                                continue
                        
                        # Skip if we've already processed this URL
                        if any(art['url'] == article_url for art in articles):
                            continue
                        
                        # Extract basic info from search result
                        title = await element.text_content()
                        title = self._clean_text(title) if title else "No title found"
                        
                        # Find date in the parent elements or surrounding text
                        date_text = ""
                        try:
                            # Look for date patterns in the page
                            page_content = await self.page.content()
                            # Find date near the article link
                            url_index = page_content.find(article_url)
                            if url_index > 0:
                                # Look in surrounding text for date pattern
                                surrounding_text = page_content[max(0, url_index-500):url_index+500]
                                date_match = re.search(r'[A-Z][a-z]+ \d{1,2}, 202[4-5] \d{2}:\d{2} ET', surrounding_text)
                                if date_match:
                                    date_text = date_match.group(0)
                        except:
                            pass
                        
                        # Quick date filter before full article processing
                        if date_text:
                            article_date = self._extract_date(date_text)
                            if article_date and not self._is_recent_article(article_date, months_back):
                                print(f"📅 Skipping old article: {title[:50]}... ({article_date})")
                                continue
                        
                        # Process the full article
                        article_data = await self._scrape_full_article(article_url, title, date_text, company_name)
                        if article_data:
                            # Final date check after full processing
                            if article_data['published_date'] and not self._is_recent_article(article_data['published_date'], months_back):
                                print(f"📅 Skipping old article after processing: {article_data['title'][:50]}... ({article_data['published_date']})")
                                continue
                            
                            # Add company context to the article data
                            article_data['target_company'] = company_name
                            articles.append(article_data)
                            articles_found_on_page += 1
                            page_articles_processed += 1
                            print(f"✅ Scraped article {len(articles)}: {article_data['title'][:50]}... ({article_data.get('published_date', 'no date')})")
                        
                        page_articles_processed += 1
                        
                        # Add delay between articles
                        await asyncio.sleep(self.delay)
                    
                    except Exception as e:
                        print(f"⚠️  Error processing article: {e}")
                        continue
                
                # Check if we should continue to next page
                if articles_found_on_page == 0 and page_articles_processed > 0:
                    print(f"📄 No new articles found on page {page_num} (all were old or duplicates)")
                    break
                elif len(article_elements) < 5:  # If very few articles on page, likely at end
                    print(f"📄 Reached end of results (only {len(article_elements)} articles on page {page_num})")
                    break
                
                page_num += 1
                
                # Add delay between pages
                await asyncio.sleep(self.delay * 2)
            
            print(f"📊 Successfully scraped {len(articles)} recent articles for {company_name} (from {page_num-1} pages)")
            
        except Exception as e:
            print(f"❌ Error searching GlobeNewswire for {company_name}: {e}")
        
        return articles
    
    async def _scrape_full_article(self, url: str, title: str, date_text: str, company_name: str) -> Optional[Dict]:
        """
        Scrape full article content from article URL
        
        Args:
            url: Article URL
            title: Article title from search results
            date_text: Date text from search results  
            company_name: Company name being searched
            
        Returns:
            Article data dictionary or None if failed
        """
        try:
            # Navigate to article page
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(1)
            
            # Extract article content
            content = ""
            
            # Try multiple selectors for article content
            content_selectors = [
                'div[class*="article-content"]',
                'div[class*="news-content"]', 
                'div[class*="press-release"]',
                '.article-body',
                '[class*="article"] p',
                'main p'
            ]
            
            for selector in content_selectors:
                content_elements = await self.page.query_selector_all(selector)
                if content_elements:
                    content_parts = []
                    for elem in content_elements:
                        text = await elem.text_content()
                        if text and len(text.strip()) > 10:  # Skip very short text
                            content_parts.append(self._clean_text(text))
                    
                    if content_parts:
                        content = "\n\n".join(content_parts)
                        break
            
            # If no structured content found, get all paragraphs
            if not content:
                p_elements = await self.page.query_selector_all('p')
                content_parts = []
                for p in p_elements:
                    text = await p.text_content()
                    text = self._clean_text(text)
                    if text and len(text) > 20:  # Skip short paragraphs
                        content_parts.append(text)
                
                content = "\n\n".join(content_parts[:10])  # Limit to first 10 paragraphs
            
            # Extract better title if available on the page
            page_title_selectors = [
                'h1',
                '.article-title',
                '[class*="headline"]',
                'title'
            ]
            
            page_title = title  # Use search result title as fallback
            for selector in page_title_selectors:
                title_element = await self.page.query_selector(selector)
                if title_element:
                    extracted_title = await title_element.text_content()
                    extracted_title = self._clean_text(extracted_title)
                    if extracted_title and len(extracted_title) > len(page_title):
                        page_title = extracted_title
                        break
            
            # Extract better date if available on the page
            page_date_selectors = [
                '[class*="date"]',
                '[class*="publish"]',
                'time',
                '.article-meta'
            ]
            
            page_date_text = date_text
            for selector in page_date_selectors:
                date_element = await self.page.query_selector(selector)
                if date_element:
                    extracted_date = await date_element.text_content()
                    if extracted_date and ('2024' in extracted_date or '2025' in extracted_date):
                        page_date_text = extracted_date
                        break
            
            # Validate we have minimum required content
            if not content or len(content.strip()) < 100:
                print(f"⚠️  Insufficient content found for article: {url}")
                return None
            
            # Check if article is actually about the company
            content_lower = content.lower()
            company_lower = company_name.lower()
            
            # Count company mentions (be more lenient for press release sites)
            company_mentions = content_lower.count(company_lower)
            if company_mentions == 0:
                # Try partial matches for compound names
                name_parts = company_lower.split()
                if len(name_parts) > 1:
                    for part in name_parts:
                        if len(part) > 3:  # Skip short words like "AI", "Co"
                            if part in content_lower:
                                company_mentions = 1
                                break
            
            if company_mentions == 0:
                print(f"⚠️  Article doesn't mention company {company_name}: {url}")
                return None
            
            return {
                'title': page_title,
                'url': url,
                'content': content,
                'published_date': self._extract_date(page_date_text),
                'source': 'globenewswire',
                'company_mentions': company_mentions,
                'content_length': len(content)
            }
            
        except Exception as e:
            print(f"❌ Error scraping article {url}: {e}")
            return None


# Example usage for testing
async def main():
    """Test function"""
    async with GlobeNewswireScraper(headless=False) as scraper:
        articles = await scraper.search_company_news("Seon", max_articles=5)
        
        print(f"\\nFound {len(articles)} articles:")
        for i, article in enumerate(articles, 1):
            print(f"{i}. {article['title']}")
            print(f"   URL: {article['url']}")
            print(f"   Date: {article['published_date']}")
            print(f"   Content length: {article['content_length']} chars")
            print(f"   Company mentions: {article['company_mentions']}")
            print()


if __name__ == "__main__":
    asyncio.run(main())
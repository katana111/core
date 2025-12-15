"""
GlobeNewswire scraper for competitor news articles.
Scrapes news articles from globenewswire.com using keyword search.
"""

import asyncio
import re
from typing import List, Dict, Optional
from urllib.parse import quote
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
    
    async def search_company_news(self, company_name: str, max_articles: int = 10) -> List[Dict]:
        """
        Search for company news on GlobeNewswire
        
        Args:
            company_name: Name of the company to search for
            max_articles: Maximum number of articles to return
            
        Returns:
            List of article dictionaries with title, url, content, date, etc.
        """
        if not self.page:
            raise RuntimeError("Browser not started. Use async context manager or call start_browser()")
        
        articles = []
        
        try:
            # Construct search URL
            search_url = f"https://www.globenewswire.com/search/keyword/{quote(company_name)}"
            print(f"🔍 Searching GlobeNewswire for: {company_name}")
            print(f"🌐 URL: {search_url}")
            
            # Navigate to search results
            await self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(self.delay)
            
            # Wait for search results to load
            try:
                await self.page.wait_for_selector('div[class*="news-article"]', timeout=10000)
            except:
                # Try alternative selectors if the first one fails
                try:
                    await self.page.wait_for_selector('a[href*="/news-release/"]', timeout=5000)
                except:
                    print(f"⚠️  No search results found for {company_name}")
                    return articles
            
            # Extract article links and basic info from search results
            article_elements = await self.page.query_selector_all('a[href*="/news-release/"]')
            
            print(f"📰 Found {len(article_elements)} potential articles")
            
            # Process each article (up to max_articles)
            processed = 0
            for element in article_elements:
                if processed >= max_articles:
                    break
                
                try:
                    # Get article URL
                    article_url = await element.get_attribute('href')
                    if not article_url or not article_url.startswith('http'):
                        if article_url and article_url.startswith('/'):
                            article_url = f"https://www.globenewswire.com{article_url}"
                        else:
                            continue
                    
                    # Extract basic info from search result
                    title_element = await element.query_selector('text=')
                    if title_element:
                        title = await title_element.text_content()
                        title = self._clean_text(title)
                    else:
                        title = "No title found"
                    
                    # Get the parent container to find date info
                    parent = await element.query_selector('xpath=ancestor::*[contains(text(), "ET") or contains(text(), "2025") or contains(text(), "2024")]')
                    date_text = ""
                    if parent:
                        parent_text = await parent.text_content()
                        # Look for date pattern in parent text
                        date_match = re.search(r'[A-Z][a-z]+ \d{1,2}, 202[45] \d{2}:\d{2} ET', parent_text)
                        if date_match:
                            date_text = date_match.group(0)
                    
                    # Process the full article
                    article_data = await self._scrape_full_article(article_url, title, date_text, company_name)
                    if article_data:
                        articles.append(article_data)
                        processed += 1
                        print(f"✅ Scraped article {processed}: {article_data['title'][:50]}...")
                    
                    # Add delay between articles
                    await asyncio.sleep(self.delay)
                
                except Exception as e:
                    print(f"⚠️  Error processing article: {e}")
                    continue
            
            print(f"📊 Successfully scraped {len(articles)} articles for {company_name}")
            
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
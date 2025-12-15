"""
Solutions Review News Scraper
Scrapes and analyzes news articles about companies from solutionsreview.com
"""

import re
import time
import asyncio
import random
from typing import Dict, List, Optional
from datetime import datetime
from urllib.parse import quote
from playwright.async_api import async_playwright, Page


class SolutionsReviewScraper:
    """Scraper for SolutionsReview.com company news"""
    
    def __init__(self, headless: bool = True):
        """
        Initialize SolutionsReview scraper
        
        Args:
            headless: Run browser in headless mode
        """
        self.headless = headless
        self.base_url = "https://solutionsreview.com"
        self.search_url = "https://solutionsreview.com/"
    
    def _random_delay(self, min_seconds: float = 1, max_seconds: float = 3):
        """Add random delay to appear more human-like"""
        time.sleep(random.uniform(min_seconds, max_seconds))
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    async def _extract_date_from_article(self, page: Page) -> str:
        """Extract publication date from article page"""
        try:
            # Common date selectors on news websites
            date_selectors = [
                '.entry-date',
                '.post-date',
                '.published',
                '.article-date',
                'time[datetime]',
                '.date'
            ]
            
            for selector in date_selectors:
                date_element = await page.query_selector(selector)
                if date_element:
                    date_text = await date_element.inner_text() or await date_element.get_attribute('datetime')
                    if date_text:
                        # Try to parse various date formats
                        date_text = self._clean_text(date_text)
                        if re.search(r'\d{4}', date_text):  # Contains year
                            return date_text
            
            # Fallback: look for date patterns in text
            page_text = await page.evaluate('() => document.body.innerText')
            date_patterns = [
                r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
                r'\d{1,2}[/-]\d{1,2}[/-]\d{4}',
                r'\d{4}-\d{2}-\d{2}'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, page_text)
                if match:
                    return match.group(0)
            
        except Exception as e:
            print(f"Error extracting date: {str(e)}")
        
        return datetime.now().strftime('%Y-%m-%d')
    
    async def _search_company_articles(self, company_name: str, max_results: int = 10) -> List[Dict]:
        """
        Search for articles about a company on SolutionsReview
        
        Args:
            company_name: Name of the company to search for
            max_results: Maximum number of articles to return
            
        Returns:
            List of article dictionaries with title, url, snippet
        """
        articles = []
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
                page = await context.new_page()
                
                # Try site search using Google (more reliable)
                search_query = f'site:solutionsreview.com "{company_name}"'
                google_search_url = f"https://www.google.com/search?q={quote(search_query)}"
                
                print(f"Searching for articles about {company_name} on SolutionsReview...")
                await page.goto(google_search_url, wait_until='domcontentloaded', timeout=30000)
                self._random_delay(2, 4)
                
                # Extract search results
                search_results = await page.query_selector_all('div[data-ved] h3')
                
                for result in search_results[:max_results]:
                    try:
                        # Get the parent link
                        link_element = await result.query_selector('xpath=ancestor::a')
                        if link_element:
                            url = await link_element.get_attribute('href')
                            if url and 'solutionsreview.com' in url:
                                title = self._clean_text(await result.inner_text())
                                
                                # Get snippet from the search result
                                snippet_element = await result.query_selector('xpath=ancestor::div[contains(@data-ved, "")]//span[contains(text(), "")]')
                                snippet = ""
                                
                                # Try to find description in parent elements
                                parent = await link_element.query_selector('xpath=following-sibling::*')
                                if parent:
                                    snippet = self._clean_text(await parent.inner_text())[:300]
                                
                                if title and len(title) > 10:
                                    articles.append({
                                        'title': title,
                                        'url': url,
                                        'snippet': snippet,
                                        'source': 'solutionsreview.com'
                                    })
                    except Exception as e:
                        continue
                
                # If Google search fails, try direct site search
                if not articles:
                    try:
                        # Try SolutionsReview's internal search if available
                        await page.goto(self.base_url, timeout=30000)
                        
                        # Look for search box
                        search_input = await page.query_selector('input[type="search"], .search-field, #s')
                        if search_input:
                            await search_input.fill(company_name)
                            await search_input.press('Enter')
                            self._random_delay(3, 5)
                            
                            # Extract results from search page
                            article_links = await page.query_selector_all('article a, .post-title a, h2 a, h3 a')
                            
                            for link in article_links[:max_results]:
                                try:
                                    title = self._clean_text(await link.inner_text())
                                    url = await link.get_attribute('href')
                                    
                                    if url and not url.startswith('http'):
                                        url = self.base_url + url
                                    
                                    if title and url and len(title) > 10:
                                        articles.append({
                                            'title': title,
                                            'url': url,
                                            'snippet': "",
                                            'source': 'solutionsreview.com'
                                        })
                                except Exception:
                                    continue
                    except Exception as e:
                        print(f"Site search failed: {str(e)}")
                
                await browser.close()
                
        except Exception as e:
            print(f"Error searching for articles: {str(e)}")
        
        return articles
    
    async def _scrape_article_content(self, article_url: str, company_name: str) -> Dict:
        """
        Scrape content from a specific article
        
        Args:
            article_url: URL of the article
            company_name: Company name for context
            
        Returns:
            Dictionary with article data
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                page = await browser.new_page()
                
                print(f"Reading article: {article_url[:60]}...")
                await page.goto(article_url, wait_until='domcontentloaded', timeout=30000)
                self._random_delay(1, 2)
                
                # Extract article content
                content_selectors = [
                    '.entry-content',
                    '.post-content',
                    '.article-content',
                    'article .content',
                    '.single-post-content',
                    'main article'
                ]
                
                content = ""
                for selector in content_selectors:
                    content_element = await page.query_selector(selector)
                    if content_element:
                        content = self._clean_text(await content_element.inner_text())
                        break
                
                # Fallback: get all paragraph text
                if not content:
                    paragraphs = await page.query_selector_all('p')
                    paragraph_texts = []
                    for p in paragraphs[:5]:
                        text = await p.inner_text()
                        paragraph_texts.append(self._clean_text(text))
                    content = ' '.join(paragraph_texts)
                
                # Extract key information relevant to the company
                relevant_content = self._extract_relevant_content(content, company_name)
                
                # Get publication date
                pub_date = await self._extract_date_from_article(page)
                
                # Get clean title
                title_element = await page.query_selector('h1, .entry-title, .post-title')
                title = self._clean_text(await title_element.inner_text()) if title_element else ""
                
                await browser.close()
                
                return {
                    'title': title[:255],
                    'content': relevant_content[:1000],
                    'url': article_url,
                    'date': pub_date,
                    'source': 'solutionsreview.com'
                }
                
        except Exception as e:
            print(f"Error scraping article {article_url}: {str(e)}")
            return {}
    
    def _extract_relevant_content(self, content: str, company_name: str) -> str:
        """
        Extract only the most relevant parts of content mentioning the company
        
        Args:
            content: Full article content
            company_name: Company name to focus on
            
        Returns:
            Relevant excerpt
        """
        if not content:
            return ""
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', content)
        relevant_sentences = []
        
        # Find sentences that mention the company
        for sentence in sentences:
            sentence = sentence.strip()
            if company_name.lower() in sentence.lower() and len(sentence) > 20:
                relevant_sentences.append(sentence)
                if len(relevant_sentences) >= 3:  # Limit to 3 key sentences
                    break
        
        # If no specific mentions, take first few sentences
        if not relevant_sentences:
            relevant_sentences = [s.strip() for s in sentences[:3] if len(s.strip()) > 20]
        
        return '. '.join(relevant_sentences) + '.'
    
    async def scrape_company_news(self, company_name: str, max_articles: int = 5) -> List[Dict]:
        """
        Search and scrape news articles about a company
        
        Args:
            company_name: Name of the company
            max_articles: Maximum number of articles to scrape
            
        Returns:
            List of article data dictionaries
        """
        print(f"Searching for news about {company_name} on SolutionsReview.com...")
        
        # First, search for articles
        articles = await self._search_company_articles(company_name, max_articles * 2)
        
        if not articles:
            print(f"No articles found for {company_name}")
            return []
        
        print(f"Found {len(articles)} potential articles, scraping content...")
        
        # Scrape content from each article
        scraped_articles = []
        for article in articles[:max_articles]:
            self._random_delay(2, 4)  # Be respectful to the server
            
            article_data = await self._scrape_article_content(article['url'], company_name)
            
            if article_data:
                # Combine search result data with scraped content
                article_data['title'] = article_data.get('title') or article['title']
                scraped_articles.append(article_data)
        
        print(f"Successfully scraped {len(scraped_articles)} articles")
        return scraped_articles
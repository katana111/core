"""
Biometric Update News Scraper
Scrapes and analyzes news articles about companies from biometricupdate.com
"""

import re
import time
import asyncio
import random
from typing import Dict, List, Optional
from datetime import datetime
from urllib.parse import quote
from playwright.async_api import async_playwright, Page


class BiometricUpdateScraper:
    """Scraper for biometricupdate.com news articles"""
    
    def __init__(self, headless: bool = True):
        """
        Initialize the scraper
        
        Args:
            headless: Whether to run browser in headless mode
        """
        self.base_url = "https://www.biometricupdate.com"
        self.headless = headless
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = ' '.join(text.split())
        
        # Remove common unwanted patterns
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[\r\n\t]+', ' ', text)
        text = text.strip()
        
        return text
    
    def _random_delay(self, min_seconds: int = 1, max_seconds: int = 3):
        """Add random delay to be respectful to the server"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    async def _extract_date_from_article(self, page: Page) -> str:
        """Extract publication date from article page"""
        try:
            # Common date selectors on BiometricUpdate
            date_selectors = [
                '.entry-date',
                '.post-date',
                '.published',
                '.article-date',
                'time[datetime]',
                '.date',
                '.post-meta time',
                '.entry-meta time'
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
        
        # Default to current date if no date found
        return datetime.now().strftime('%B %d, %Y')
    
    async def _search_company_articles(self, company_name: str, max_results: int = 10) -> List[Dict]:
        """
        Search for articles about a company on BiometricUpdate
        
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
                search_query = f'site:biometricupdate.com "{company_name}"'
                google_search_url = f"https://www.google.com/search?q={quote(search_query)}"
                
                print(f"Searching for articles about {company_name} on BiometricUpdate...")
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
                            if url and 'biometricupdate.com' in url:
                                title = self._clean_text(await result.inner_text())
                                
                                # Get snippet from the search result
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
                                        'source': 'biometricupdate.com'
                                    })
                    except Exception as e:
                        continue
                
                # If Google search fails, try direct site search
                if not articles:
                    try:
                        # Try BiometricUpdate's internal search if available
                        await page.goto(self.base_url, timeout=30000)
                        
                        # Look for search box
                        search_input = await page.query_selector('input[type="search"], .search-field, #s, .search-input')
                        if search_input:
                            await search_input.fill(company_name)
                            await search_input.press('Enter')
                            self._random_delay(3, 5)
                            
                            # Extract results from search page
                            article_links = await page.query_selector_all('article a, .post-title a, h2 a, h3 a, .entry-title a')
                            
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
                                            'source': 'biometricupdate.com'
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
                    'main article',
                    '.post-body',
                    '.article-body'
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
                    for p in paragraphs[:8]:  # Get more paragraphs for biometric articles
                        text = await p.inner_text()
                        paragraph_texts.append(self._clean_text(text))
                    content = ' '.join(paragraph_texts)
                
                # Extract key information relevant to the company
                relevant_content = self._extract_relevant_content(content, company_name)
                
                # Get publication date
                pub_date = await self._extract_date_from_article(page)
                
                # Get clean title
                title_element = await page.query_selector('h1, .entry-title, .post-title, .article-title')
                title = self._clean_text(await title_element.inner_text()) if title_element else ""
                
                await browser.close()
                
                return {
                    'title': title[:255],
                    'content': relevant_content[:1000],
                    'url': article_url,
                    'date': pub_date,
                    'source': 'biometricupdate.com'
                }
                
        except Exception as e:
            print(f"Error scraping article {article_url}: {str(e)}")
            return {}
    
    def _extract_relevant_content(self, content: str, company_name: str) -> str:
        """
        Extract sentences most relevant to the company
        
        Args:
            content: Full article content
            company_name: Company name to focus on
            
        Returns:
            Relevant content focused on the company
        """
        if not content:
            return ""
        
        sentences = re.split(r'[.!?]+', content)
        relevant_sentences = []
        
        # Look for sentences mentioning the company
        company_variations = [
            company_name.lower(),
            company_name.lower().replace(' ', ''),
            company_name.split()[0].lower() if ' ' in company_name else company_name.lower()
        ]
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:  # Skip very short sentences
                continue
            
            sentence_lower = sentence.lower()
            
            # Check if sentence contains company name or variations
            for variation in company_variations:
                if variation in sentence_lower:
                    relevant_sentences.append(sentence)
                    break
            
            # Also include sentences with biometric/security keywords + company context
            biometric_keywords = ['biometric', 'authentication', 'identity', 'security', 'fraud', 'verification', 'facial', 'fingerprint', 'iris', 'voice']
            if any(keyword in sentence_lower for keyword in biometric_keywords) and len(relevant_sentences) < 3:
                # Check if this sentence is near company mentions
                if any(var in content.lower()[max(0, content.lower().find(sentence_lower)-200):content.lower().find(sentence_lower)+200] for var in company_variations):
                    relevant_sentences.append(sentence)
        
        # Limit to top 3 most relevant sentences
        if len(relevant_sentences) > 3:
            relevant_sentences = relevant_sentences[:3]
        elif not relevant_sentences and content:
            # Fallback: get first few sentences if no specific company mentions
            first_sentences = [s.strip() for s in sentences[:3] if len(s.strip()) > 20]
            relevant_sentences = first_sentences
        
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
        print(f"Searching for news about {company_name} on BiometricUpdate.com...")
        
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
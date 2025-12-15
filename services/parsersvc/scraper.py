"""
Parsers.vc Company Data Scraper
Fetches company information from parsers.vc
"""

import re
import time
import random
from typing import Dict, Optional
from datetime import datetime
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError


class ParsersVCScraper:
    """Scraper for Parsers.vc company data"""
    
    def __init__(self, headless: bool = True):
        """
        Initialize Parsers.vc scraper
        
        Args:
            headless: Run browser in headless mode
        """
        self.headless = headless
        self.base_url = "https://parsers.vc/startup/"
    
    def _random_delay(self, min_seconds: float = 1, max_seconds: float = 2):
        """Add random delay to appear more human-like"""
        time.sleep(random.uniform(min_seconds, max_seconds))
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _extract_location(self, page: Page) -> str:
        """Extract company location"""
        try:
            body_text = page.evaluate('() => document.body.innerText')
            
            # Pattern: "Location: <location>"
            patterns = [
                r'Location[:\s]+([^\n]+)',
                r'Headquarters[:\s]+([^\n]+)',
                r'Based in[:\s]+([^\n]+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, body_text, re.IGNORECASE)
                if match:
                    location = self._clean_text(match.group(1))
                    # Stop at common section markers
                    location = re.split(r'\s+(?:Employees|Founded|Total|Stage)', location, flags=re.IGNORECASE)[0]
                    if location and len(location) > 2 and len(location) < 100:
                        return location
        except Exception as e:
            print(f"Error extracting location: {str(e)}")
        return ""
    
    def _extract_employees(self, page: Page) -> str:
        """Extract employee count"""
        try:
            body_text = page.evaluate('() => document.body.innerText')
            
            patterns = [
                r'Employees[:\s]+(\d+(?:\s*-\s*\d+)?)',
                r'Employee count[:\s]+(\d+(?:\s*-\s*\d+)?)',
                r'Team size[:\s]+(\d+(?:\s*-\s*\d+)?)',
                r'(\d+\s*-\s*\d+)\s+employees',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, body_text, re.IGNORECASE)
                if match:
                    employees = self._clean_text(match.group(1))
                    if employees:
                        return employees
        except Exception as e:
            print(f"Error extracting employees: {str(e)}")
        return ""
    
    def _extract_total_raised(self, page: Page) -> Optional[float]:
        """
        Extract total funding raised and convert to numeric value
        
        Returns:
            Float value in base currency or None
        """
        try:
            body_text = page.evaluate('() => document.body.innerText')
            
            patterns = [
                r'Total\s+(?:funding\s+)?raised[:\s]+\$?([\d.]+)\s*([MBK])?',
                r'Funding[:\s]+\$?([\d.]+)\s*([MBK])?',
                r'raised\s+\$?([\d.]+)\s*([MBK])?',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, body_text, re.IGNORECASE)
                if match:
                    amount_str = match.group(1)
                    unit = match.group(2).upper() if match.group(2) else None
                    
                    try:
                        amount = float(amount_str)
                        
                        if unit == 'B':
                            return amount * 1000000000
                        elif unit == 'M':
                            return amount * 1000000
                        elif unit == 'K':
                            return amount * 1000
                        else:
                            return amount
                    except ValueError:
                        continue
        except Exception as e:
            print(f"Error extracting total raised: {str(e)}")
        return None
    
    def _extract_founded_year(self, page: Page) -> str:
        """Extract founded year"""
        try:
            body_text = page.evaluate('() => document.body.innerText')
            
            patterns = [
                r'Founded[:\s]+(\d{4})',
                r'Established[:\s]+(\d{4})',
                r'Founded in[:\s]+(\d{4})',
                r'Since[:\s]+(\d{4})',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, body_text, re.IGNORECASE)
                if match:
                    year = match.group(1)
                    # Validate year is reasonable (between 1900 and current year + 1)
                    if 1900 <= int(year) <= datetime.now().year + 1:
                        return year
        except Exception as e:
            print(f"Error extracting founded year: {str(e)}")
        return ""
    
    def _extract_categories(self, page: Page) -> list:
        """Extract company categories/tags"""
        try:
            body_text = page.evaluate('() => document.body.innerText')
            
            # Pattern: "Categories:" or "Tags:" followed by comma-separated values
            patterns = [
                r'Categories[:\s]+([^\n]+)',
                r'Tags[:\s]+([^\n]+)',
                r'Industry[:\s]+([^\n]+)',
                r'Sectors[:\s]+([^\n]+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, body_text, re.IGNORECASE)
                if match:
                    categories_str = self._clean_text(match.group(1))
                    # Stop at common section markers
                    categories_str = re.split(r'\s+(?:Location|Founded|Employees|Total|Stage)', categories_str, flags=re.IGNORECASE)[0]
                    
                    # Try different splitting methods
                    # First try comma or semicolon
                    if ',' in categories_str or ';' in categories_str:
                        categories = re.split(r'[,;]', categories_str)
                    # If no delimiters, try to split by capital letters (camelCase)
                    elif categories_str and categories_str[0].isupper():
                        # Use regex to split camelCase/PascalCase: 
                        # Matches: Capital letters followed by lowercase OR multiple capitals (acronyms)
                        # Handles: AI, AML, Compliance, SaaS, etc.
                        categories = re.findall(r'[A-Z](?:[a-z]+|[A-Z]*(?=[A-Z][a-z]|\b))', categories_str)
                    else:
                        # Split by spaces if present
                        categories = categories_str.split()
                    
                    # Clean, filter and deduplicate
                    seen = set()
                    unique_categories = []
                    for cat in categories:
                        cat = cat.strip()
                        # Filter: length > 1, not already seen
                        if len(cat) > 1 and cat.lower() not in seen:
                            seen.add(cat.lower())
                            unique_categories.append(cat)
                    
                    categories = unique_categories
                    
                    if categories:
                        return categories
        except Exception as e:
            print(f"Error extracting categories: {str(e)}")
        return []
    
    def _extract_press_mentions(self, page: Page) -> list:
        """Extract press mentions and media coverage from parsers.vc"""
        mentions = []
        try:
            body_text = page.evaluate('() => document.body.innerText')
            
            # Find "Mentions in press and media" section
            if 'Mentions in press and media' not in body_text:
                return []
            
            # Split into lines and find the section
            lines = body_text.split('\n')
            in_press_section = False
            
            for i, line in enumerate(lines):
                if 'Mentions in press and media' in line:
                    in_press_section = True
                    # Skip the header lines (usually next 1-2 lines)
                    continue
                
                if in_press_section:
                    line = line.strip()
                    
                    # Stop at next major section or empty lines
                    if not line:
                        continue
                    if line in ['Investors', 'Funding Rounds', 'Competitors', 'Team', 'LinkedIn']:
                        break
                    
                    # Look for date pattern at start of line (DD.MM.YYYY format used by parsers.vc)
                    date_match = re.match(r'(\d{2}\.\d{2}\.\d{4})\s+(.+)', line)
                    
                    if date_match:
                        date_str = date_match.group(1)
                        rest_of_line = date_match.group(2).strip()
                        
                        # Parse the line: usually "Date Title Description Source"
                        # Title is often the first major part
                        if rest_of_line and len(rest_of_line) > 10:
                            # Split on multiple spaces or try to identify title vs description
                            parts = rest_of_line.split('  ')  # Double space separator
                            if len(parts) >= 2:
                                title = parts[0].strip()
                                description = ' '.join(parts[1:]).strip()
                            else:
                                # Try splitting at first sentence
                                sentences = rest_of_line.split('. ')
                                if len(sentences) > 1:
                                    title = sentences[0] + '.'
                                    description = '. '.join(sentences[1:])
                                else:
                                    # Use first 150 chars as title, rest as description
                                    title = rest_of_line[:150]
                                    description = rest_of_line
                            
                            mentions.append({
                                'date': date_str,
                                'title': self._clean_text(title)[:300],
                                'content': self._clean_text(description)[:1000],
                                'url': ''
                            })
            
            if mentions:
                print(f"Found {len(mentions)} press mentions")
            
        except Exception as e:
            print(f"Error extracting press mentions: {str(e)}")
        
        return mentions
    
    def scrape_company(self, website: str, max_retries: int = 3) -> Optional[Dict]:
        """
        Scrape company data from parsers.vc
        
        Args:
            website: Company website (without http/https prefix, e.g., 'seon.io')
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dictionary with company data or None if failed
        """
        # Clean website - remove protocol if present
        website = re.sub(r'^https?://', '', website)
        website = website.strip('/')
        
        url = f"{self.base_url}{website}"
        attempt = 0
        last_error = None
        
        while attempt < max_retries:
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=self.headless)
                    context = browser.new_context(
                        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                    )
                    page = context.new_page()
                    
                    print(f"Navigating to: {url}")
                    page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    
                    # Wait for content to load
                    try:
                        page.wait_for_selector('body', timeout=10000)
                    except:
                        print("Warning: Timeout waiting for page content")
                    
                    self._random_delay(1, 2)
                    
                    # Extract company data
                    company_data = {
                        'website': website,
                        'scraped_at': datetime.now().isoformat(),
                        'location': '',
                        'employees': '',
                        'total_raised': None,
                        'founded_year': '',
                        'categories': [],
                        'press_mentions': []
                    }
                    
                    print("Extracting data from parsers.vc...")
                    company_data['location'] = self._extract_location(page)
                    company_data['employees'] = self._extract_employees(page)
                    company_data['total_raised'] = self._extract_total_raised(page)
                    company_data['founded_year'] = self._extract_founded_year(page)
                    company_data['categories'] = self._extract_categories(page)
                    company_data['press_mentions'] = self._extract_press_mentions(page)
                    
                    browser.close()
                    
                    print(f"Successfully scraped: {website}")
                    return company_data
                    
            except Exception as e:
                last_error = e
                attempt += 1
                print(f"Attempt {attempt} failed: {str(e)}")
                
                if attempt < max_retries:
                    print(f"Retrying... ({attempt}/{max_retries})")
                    self._random_delay(3, 5)
        
        print(f"Failed to scrape after {max_retries} attempts. Last error: {str(last_error)}")
        return None

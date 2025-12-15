"""
Tracxn Company Data Scraper
Fetches company information from Tracxn.com with proxy support
"""

import json
import time
import random
from typing import Dict, Optional, List
from datetime import datetime
from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError
import os

# Handle both relative and absolute imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

try:
    from .proxy_config import ProxyManager
    from .db_operations import CompetitorDB
except ImportError:
    from proxy_config import ProxyManager
    from db_operations import CompetitorDB


class TracxnScraper:
    """Scraper for Tracxn company data"""

    def __init__(self, proxy_manager: Optional[ProxyManager] = None, headless: bool = True,
                 save_to_db: bool = False):
        """
        Initialize Tracxn scraper

        Args:
            proxy_manager: ProxyManager instance for proxy rotation
            headless: Run browser in headless mode
            save_to_db: Whether to save scraped data to database (uses centralized DB connection)
        """
        self.proxy_manager = proxy_manager
        self.headless = headless
        self.save_to_db = save_to_db
        self.db_operations = None

        if self.save_to_db:
            self.db_operations = CompetitorDB()

        self.output_dir = os.path.join(os.path.dirname(__file__), 'data')
        self.output_file = os.path.join(self.output_dir, 'tracxn_companies.json')

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

    def _get_proxy_config(self) -> Optional[Dict]:
        """Get proxy configuration for Playwright"""
        if not self.proxy_manager:
            return None

        proxy_dict = self.proxy_manager.get_proxy()
        if not proxy_dict:
            return None

        # Parse proxy URL
        proxy_url = proxy_dict.get('http', '')
        if proxy_url:
            # Format: http://user:pass@host:port or http://host:port
            if '@' in proxy_url:
                auth_part, server_part = proxy_url.split('@')
                protocol = auth_part.split('://')[0]
                username_password = auth_part.split('://')[1]
                username, password = username_password.split(':')
                server, port = server_part.split(':')

                return {
                    'server': f'{protocol}://{server}:{port}',
                    'username': username,
                    'password': password
                }
            else:
                # No authentication
                return {'server': proxy_url}

        return None

    def _random_delay(self, min_seconds: float = 1, max_seconds: float = 3):
        """Add random delay to appear more human-like"""
        time.sleep(random.uniform(min_seconds, max_seconds))

    def _extract_text(self, page: Page, selector: str, timeout: int = 3000) -> str:
        """Safely extract text from element"""
        try:
            element = page.wait_for_selector(selector, timeout=timeout)
            if element:
                return element.inner_text().strip()
        except:
            pass
        return ""

    def _extract_text_content(self, page: Page, text_pattern: str) -> str:
        """Extract text by pattern matching"""
        try:
            content = page.content()
            import re
            match = re.search(text_pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        except:
            pass
        return ""

    def _extract_key_metrics(self, page: Page) -> Dict:
        """Extract key metrics section efficiently"""
        metrics = {
            'founded_year': '',
            'location': '',
            'funding_stage': '',
            'fundings_amount': '',
            'total_funding': '',
            'latest_funding_round': '',
            'employee_count': '',
            'exit_details': '',
            'acquisitions': [],
            'annual_revenue': '',
        }

        try:
            # Get text content directly from page for better extraction
            import re
            page_text = page.content()

            # Try to get visible text content as well
            try:
                body_text = page.evaluate('() => document.body.innerText')
            except:
                body_text = page_text

            # Extract Founded Year - multiple patterns
            founded_patterns = [
                r'Founded[:\s]+(\d{4})',
                r'founded[:\s]+(\d{4})',
                r'Founded Year[:\s]+(\d{4})',
            ]
            for pattern in founded_patterns:
                match = re.search(pattern, body_text)
                if match:
                    metrics['founded_year'] = match.group(1)
                    break

            # Extract Location - more flexible
            location_patterns = [
                r'Location[:\s]+([^\n]+?)(?:Stage|Total|$)',
                r'based in[:\s]+([^\n,]+)',
                r'headquartered in[:\s]+([^\n,]+)',
            ]
            for pattern in location_patterns:
                match = re.search(pattern, body_text, re.IGNORECASE)
                if match:
                    location = match.group(1).strip()
                    # Clean up
                    location = re.sub(r'\s+', ' ', location)
                    if location and len(location) > 3:
                        metrics['location'] = location
                        break

            # Extract Funding Stage - improved patterns
            stage_patterns = [
                r'Stage\s+(Series [A-Z]|Seed|Angel|Pre-Seed|Private Equity|Public|Acquired)',
                r'Stage:\s*([^\n]+?)(?:\s|$)',
                r'is a\s+(Series [A-Z]|Seed|Angel|Pre-Seed)\s+company',
                r'company\s+based[^,]+,\s+founded[^,]+\.\s+It\s+operates\s+as\s+a\s+([^.]+)',
            ]
            for pattern in stage_patterns:
                match = re.search(pattern, body_text, re.IGNORECASE)
                if match:
                    stage = match.group(1).strip()
                    # Clean up stage value
                    stage = re.sub(r'Total Funding.*$', '', stage).strip()
                    if stage and len(stage) < 50 and not stage.isdigit():
                        metrics['funding_stage'] = stage
                        break

            # Extract Total Funding - multiple patterns
            funding_patterns = [
                r'Total Funding[:\s]+\$?([\d.]+[BMK])',
                r'raised[:\s]+\$?([\d.]+[BMK])',
                r'has raised[:\s]+\$?([\d.]+[BMK])',
            ]
            for pattern in funding_patterns:
                match = re.search(pattern, body_text, re.IGNORECASE)
                if match:
                    metrics['total_funding'] = '$' + match.group(1)
                    break

            # Extract Latest Funding Round
            latest_patterns = [
                r'Latest Funding Round[:\s]+([^\n]+?)(?=Key Metrics|Employee|$)',
                r'latest round was[:\s]+([^\n]+)',
            ]
            for pattern in latest_patterns:
                match = re.search(pattern, body_text, re.IGNORECASE)
                if match:
                    latest = match.group(1).strip()
                    if len(latest) > 5 and len(latest) < 200:
                        metrics['latest_funding_round'] = latest
                        break

            # Extract Employee Count
            employee_patterns = [
                r'(\d+\s*-\s*\d+)\s+employees',
                r'has[:\s]+(\d+\s*-\s*\d+)\s+employees',
            ]
            for pattern in employee_patterns:
                match = re.search(pattern, body_text, re.IGNORECASE)
                if match:
                    metrics['employee_count'] = match.group(1)
                    break

            # Extract Annual Revenue
            revenue_patterns = [
                r'Annual Revenue[:\s]+\$?([\d.]+[BMK])',
                r'revenue[:\s]+\$?([\d.]+[BMK])',
            ]
            for pattern in revenue_patterns:
                match = re.search(pattern, body_text, re.IGNORECASE)
                if match:
                    metrics['annual_revenue'] = match.group(1)
                    break

        except Exception as e:
            print(f"Error extracting key metrics: {str(e)}")

        return metrics

    def _extract_funding_rounds(self, page: Page) -> List[Dict]:
        """Extract funding rounds from table"""
        rounds = []
        try:
            import re

            # Get visible text
            try:
                body_text = page.evaluate('() => document.body.innerText')
            except:
                body_text = page.content()

            # Pattern to match funding rounds - more flexible
            # Looking for patterns like: "Sep 16, 2025 | $80M | Series C"
            rounds_patterns = [
                r'([A-Z][a-z]+\s+\d{1,2},\s+\d{4})[^\n]*?\$?([\d.]+[BMK])[^\n]*?(Series [A-Z]|Seed|Angel|Pre-seed)',
                r'(\d{4}-\d{2}-\d{2})[^\n]*?\$?([\d.]+[BMK])[^\n]*?(Series [A-Z]|Seed|Angel)',
            ]

            for pattern in rounds_patterns:
                matches = re.finditer(pattern, body_text, re.IGNORECASE)
                for match in matches:
                    round_data = {
                        'date': match.group(1),
                        'amount': '$' + match.group(2),
                        'round_type': match.group(3).strip()
                    }
                    # Avoid duplicates
                    if round_data not in rounds:
                        rounds.append(round_data)

            # If no rounds found, try alternative pattern from HTML
            if not rounds:
                page_html = page.content()
                # Look for table-like structures
                table_pattern = r'<tr[^>]*>.*?(\w+\s+\d+,\s+\d{4}).*?\$?([\d.]+[BMK]).*?(Series [A-Z]|Seed|Angel).*?</tr>'
                matches = re.finditer(table_pattern, page_html, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    rounds.append({
                        'date': match.group(1),
                        'amount': '$' + match.group(2),
                        'round_type': match.group(3).strip()
                    })

        except Exception as e:
            print(f"Error extracting funding rounds: {str(e)}")

        return rounds

    def _extract_registered_address(self, page: Page) -> str:
        """Extract registered address"""
        try:
            import re
            # Get visible text
            try:
                body_text = page.evaluate('() => document.body.innerText')
            except:
                body_text = page.content()

            # Primary pattern: "Its registered address is <address>. Its corporate identification"
            match = re.search(
                r'registered address is\s+(.+?)\.\s*Its\s+corporate',
                body_text,
                re.IGNORECASE | re.DOTALL
            )
            
            if match:
                address = match.group(1).strip()
                address = re.sub(r'\s+', ' ', address).strip()
                if len(address) > 20 and len(address) < 300:
                    return address
            
            # Fallback 1: Stop at "Its" (any "Its")
            match = re.search(
                r'registered address is\s+(.+?)\.\s*Its',
                body_text,
                re.IGNORECASE | re.DOTALL
            )
            
            if match:
                address = match.group(1).strip()
                address = re.sub(r'\s+', ' ', address).strip()
                if len(address) > 20 and len(address) < 300:
                    return address
            
            # Fallback 2: Match "Registered Address: <address>" but stop at section markers
            match = re.search(
                r'Registered Address[:\s]+(.+?)(?:\s+Key Metrics|\s+Founded|\s+Location|\s+Stage|\s+Total Funding|\s+Employee|$)',
                body_text,
                re.IGNORECASE | re.DOTALL
            )
            
            if match:
                address = match.group(1).strip()
                # Clean up extra whitespace and newlines
                address = re.sub(r'\s+', ' ', address).strip()
                # Remove trailing period
                address = address.rstrip('.')
                # Check if address has postal code and clean up anything after it
                postal_match = re.search(r'(\d{5,6})\s+[A-Z]', address)
                if postal_match:
                    # Cut at the end of postal code (before the capital letter that starts next section)
                    postal_end = address.find(postal_match.group(1)) + len(postal_match.group(1))
                    address = address[:postal_end].strip()
                
                if len(address) > 20 and len(address) < 300:
                    return address
                        
        except Exception as e:
            print(f"Error extracting address: {str(e)}")
        return ""

    def _extract_investors(self, page: Page) -> List[str]:
        """Extract investor information"""
        investors = []
        try:
            import re
            # Get visible text
            try:
                body_text = page.evaluate('() => document.body.innerText')
            except:
                body_text = page.content()

            # Look for institutional investors pattern
            investors_patterns = [
                r'has\s+(\d+)\s+institutional investors including\s+([^\n]+?)(?:\.|and)',
                r'investors include\s+([^\n]+?)(?:\.|and)',
                r'backed by\s+([^\n]+?)(?:\.|and)',
            ]

            for pattern in investors_patterns:
                match = re.search(pattern, body_text, re.IGNORECASE)
                if match:
                    # Get the investor text
                    if len(match.groups()) > 1:
                        investor_text = match.group(2)
                    else:
                        investor_text = match.group(1)

                    # Split by common separators
                    for sep in [',', ' and ', ';']:
                        if sep in investor_text:
                            parts = investor_text.split(sep)
                            for part in parts:
                                name = part.strip()
                                # Clean up
                                name = re.sub(r'\[\d+\]', '', name)  # Remove reference numbers
                                name = re.sub(r'^and\s+', '', name, flags=re.IGNORECASE)
                                if name and len(name) > 2 and len(name) < 100:
                                    investors.append(name)
                    break

            # Try to find from funding table context
            if not investors:
                # Look for lead investors in funding rounds
                lead_pattern = r'lead by\s+([^,\n]+)|led by\s+([^,\n]+)'
                matches = re.finditer(lead_pattern, body_text, re.IGNORECASE)
                for match in matches:
                    lead = match.group(1) or match.group(2)
                    if lead:
                        investors.append(lead.strip())

        except Exception as e:
            print(f"Error extracting investors: {str(e)}")

        return list(set(investors))[:20]  # Deduplicate and limit

    def _extract_acquisitions(self, page: Page) -> List[Dict]:
        """Extract detailed acquisition information"""
        acquisitions = []
        try:
            import re
            # Get visible text
            try:
                body_text = page.evaluate('() => document.body.innerText')
            except:
                body_text = page.content()

            # Pattern 1: "has acquired [CompanyName]"
            acq_match = re.search(r'has acquired\s+([A-Z][a-zA-Z\s&.]+?)(?:\.| SEON| has)', body_text, re.IGNORECASE)
            if acq_match:
                company = acq_match.group(1).strip()
                # Clean up
                company = re.sub(r'^(the|a|an)\s+', '', company, flags=re.IGNORECASE)
                company = re.sub(r'\s+', ' ', company).strip()
                if company and len(company) > 2 and len(company) < 100:
                    acquisitions.append({
                        'company': company,
                        'date': '',
                        'amount': ''
                    })

            # Pattern 2: Look in "Investments and acquisitions" section
            inv_acq_section = re.search(r'Investments and acquisitions[^\n]*has acquired\s+([^\n]+)', body_text, re.IGNORECASE)
            if inv_acq_section and not acquisitions:
                acq_text = inv_acq_section.group(1).strip()
                # Extract company name before period or "has not"
                company_match = re.search(r'^([A-Z][a-zA-Z\s&.]+?)(?:\.| SEON| has)', acq_text)
                if company_match:
                    company = company_match.group(1).strip()
                    company = re.sub(r'\s+', ' ', company).strip()
                    if company and len(company) > 2 and len(company) < 100:
                        acquisitions.append({
                            'company': company,
                            'date': '',
                            'amount': ''
                        })

            # Pattern 3: Multiple acquisitions separated by commas
            multi_acq = re.search(r'has acquired\s+([A-Z][^.]+?)\s+and\s+([A-Z][^.]+)\.', body_text, re.IGNORECASE)
            if multi_acq and not acquisitions:
                for i in range(1, 3):
                    company = multi_acq.group(i).strip()
                    company = re.sub(r'\s+', ' ', company).strip()
                    if company and len(company) > 2 and len(company) < 100:
                        acquisitions.append({
                            'company': company,
                            'date': '',
                            'amount': ''
                        })

        except Exception as e:
            print(f"Error extracting acquisitions: {str(e)}")

        return acquisitions

    def _extract_investments(self, page: Page) -> List[Dict]:
        """Extract investments made by the company"""
        investments = []
        try:
            import re
            # Get visible text
            try:
                body_text = page.evaluate('() => document.body.innerText')
            except:
                body_text = page.content()

            # Look for "has not made any investments" pattern - return empty list
            no_investments = re.search(r'has not made any\s*investments', body_text, re.IGNORECASE)
            if no_investments:
                print("Company has not made any investments")
                return []

            # Look for "has made X investments" - this indicates investments exist
            has_investments = re.search(r'has made\s+(\d+)\s+investments?', body_text, re.IGNORECASE)
            if has_investments:
                count = has_investments.group(1)
                print(f"Found {count} investments mentioned (but no details available on free tier)")
                # Note: Detailed investment list may require premium access
                # Return indicator that investments exist but details not available
                return [{'company': f'Note: {count} investments made (details require premium access)', 'date': '', 'amount': ''}]

            # Try to extract if company names are listed
            invested_in = re.search(r'invested in\s+([A-Z][^.]+)\.', body_text, re.IGNORECASE)
            if invested_in:
                inv_text = invested_in.group(1).strip()
                # Split by common separators
                companies = re.split(r',\s*(?=and|[A-Z])|\s+and\s+', inv_text)
                for company in companies:
                    company = company.strip()
                    company = re.sub(r'^(the|a|an)\s+', '', company, flags=re.IGNORECASE)
                    if company and len(company) > 2 and len(company) < 100:
                        investments.append({
                            'company': company,
                            'date': '',
                            'amount': ''
                        })

        except Exception as e:
            print(f"Error extracting investments: {str(e)}")

        return investments

    def _extract_exit_details(self, page: Page) -> str:
        """Extract exit information (IPO, Acquired, etc.)"""
        try:
            import re
            # Get visible text
            try:
                body_text = page.evaluate('() => document.body.innerText')
            except:
                body_text = page.content()

            # Check for acquisition or IPO
            if re.search(r'Stage[:\s]+Acquired', body_text, re.IGNORECASE):
                return "Acquired"
            elif re.search(r'Stage[:\s]+Public', body_text, re.IGNORECASE):
                return "IPO (Public)"
        except Exception as e:
            print(f"Error extracting exit details: {str(e)}")
        return ""

    def scrape_company(self, company_url: str, company_name: Optional[str] = None, max_retries: int = 3) -> Optional[Dict]:
        """
        Scrape company data from Tracxn

        Args:
            company_url: Full URL to company page on Tracxn (e.g., https://tracxn.com/d/companies/company-name)
            company_name: Optional company name to use instead of extracting from page
            max_retries: Maximum number of retry attempts

        Returns:
            Dictionary with company data or None if failed
        """
        attempt = 0
        last_error = None

        while attempt < max_retries:
            try:
                with sync_playwright() as p:
                    # Get proxy configuration
                    proxy_config = self._get_proxy_config()

                    # Launch browser with proxy
                    launch_options = {
                        'headless': self.headless,
                    }

                    if proxy_config:
                        launch_options['proxy'] = proxy_config
                        print(f"Using proxy: {proxy_config.get('server', 'N/A')}")

                    browser = p.chromium.launch(**launch_options)
                    context = browser.new_context(
                        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    )
                    page = context.new_page()

                    # Navigate to company page
                    print(f"Navigating to: {company_url}")
                    page.goto(company_url, wait_until='domcontentloaded', timeout=30000)

                    # Wait for main content to load
                    try:
                        page.wait_for_selector('h1', timeout=10000)
                    except:
                        print("Warning: Timeout waiting for page content")

                    self._random_delay(1, 2)

                    # Extract company data efficiently
                    company_data = {
                        'url': company_url,
                        'scraped_at': datetime.now().isoformat(),
                        'company_name': '',
                        'description': '',
                        'fundings': {
                            'total_funding': '',
                            'funding_rounds': [],
                            'latest_funding_round': '',
                            'investors': []
                        },
                        'employee_count': '',
                        'location': '',
                        'funding_stage': '',
                        'exit_details': '',
                        'founded_year': '',
                        'acquisitions': [],
                        'investments': [],
                        'founded_at': '',
                        'main_office': '',
                        'registered_address': ''
                    }

                    # Company name - use provided or extract from h1
                    if company_name:
                        company_data['company_name'] = company_name
                    else:
                        try:
                            h1_element = page.query_selector('h1')
                            if h1_element:
                                company_data['company_name'] = h1_element.inner_text().strip()
                        except:
                            pass

                    # Extract key metrics section (most efficient method)
                    print("Extracting key metrics...")
                    metrics = self._extract_key_metrics(page)
                    company_data['founded_year'] = metrics.get('founded_year', '')
                    company_data['founded_at'] = metrics.get('founded_year', '')
                    company_data['location'] = metrics.get('location', '')
                    company_data['main_office'] = metrics.get('location', '')
                    company_data['funding_stage'] = metrics.get('funding_stage', '')
                    company_data['fundings']['total_funding'] = metrics.get('total_funding', '')
                    company_data['fundings']['latest_funding_round'] = metrics.get('latest_funding_round', '')
                    company_data['employee_count'] = metrics.get('employee_count', '')

                    # Extract registered address
                    company_data['registered_address'] = self._extract_registered_address(page)

                    # Extract funding rounds
                    print("Extracting funding rounds...")
                    company_data['fundings']['funding_rounds'] = self._extract_funding_rounds(page)

                    # Extract investors
                    print("Extracting investors...")
                    company_data['fundings']['investors'] = self._extract_investors(page)

                    # Extract acquisitions
                    print("Extracting acquisitions...")
                    company_data['acquisitions'] = self._extract_acquisitions(page)

                    # Extract investments made by company
                    print("Extracting investments...")
                    company_data['investments'] = self._extract_investments(page)

                    # Extract exit details
                    company_data['exit_details'] = self._extract_exit_details(page)

                    browser.close()

                    # Mark proxy as successful
                    if proxy_config and self.proxy_manager:
                        self.proxy_manager.mark_proxy_success({'http': proxy_config.get('server', '')})

                    # Save to database if enabled
                    if self.save_to_db and self.db_operations:
                        print("Saving to database...")
                        competitor_id = self.db_operations.save_competitor(company_data)
                        if competitor_id:
                            company_data['db_competitor_id'] = competitor_id

                    print(f"Successfully scraped: {company_data['company_name']}")
                    return company_data

            except Exception as e:
                last_error = e
                attempt += 1
                print(f"Attempt {attempt} failed: {str(e)}")

                # Mark proxy as failed if using proxy
                if self.proxy_manager:
                    proxy_dict = self.proxy_manager.get_proxy()
                    if proxy_dict:
                        self.proxy_manager.mark_proxy_failed(proxy_dict)

                if attempt < max_retries:
                    print(f"Retrying... ({attempt}/{max_retries})")
                    self._random_delay(3, 6)

        print(f"Failed to scrape after {max_retries} attempts. Last error: {str(last_error)}")
        return None

    def scrape_companies(self, company_urls: List[str], company_names: Optional[List[str]] = None) -> List[Dict]:
        """
        Scrape multiple companies

        Args:
            company_urls: List of Tracxn company URLs
            company_names: Optional list of company names (must match length of company_urls)

        Returns:
            List of company data dictionaries
        """
        # Validate company_names length if provided
        if company_names and len(company_names) != len(company_urls):
            print(f"Warning: company_names length ({len(company_names)}) doesn't match company_urls length ({len(company_urls)})")
            company_names = None
        
        results = []

        for i, url in enumerate(company_urls, 1):
            print(f"\n{'='*60}")
            print(f"Scraping company {i}/{len(company_urls)}")
            print(f"{'='*60}")

            # Get company name if provided
            name = company_names[i-1] if company_names else None
            
            company_data = self.scrape_company(url, company_name=name)
            if company_data:
                results.append(company_data)
                self.save_results(results)

            # Random delay between companies
            if i < len(company_urls):
                self._random_delay(5, 10)

        # Print database save summary if enabled
        if self.save_to_db and self.db_operations and results:
            db_saved = sum(1 for r in results if 'db_competitor_id' in r)
            print(f"\n{'='*60}")
            print(f"DATABASE SAVE SUMMARY")
            print(f"{'='*60}")
            print(f"Total scraped: {len(results)}")
            print(f"Saved to DB: {db_saved}")
            print(f"{'='*60}\n")

        return results

    def save_results(self, results: List[Dict]):
        """Save results to JSON file"""
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"\nResults saved to: {self.output_file}")
        except Exception as e:
            print(f"Error saving results: {str(e)}")

    def load_results(self) -> List[Dict]:
        """Load existing results from file"""
        try:
            if os.path.exists(self.output_file):
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading results: {str(e)}")
        return []

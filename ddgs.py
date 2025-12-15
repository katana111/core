"""
Model Agent for Company Industry Search using DuckDuckGo Chat (DDGC)
"""

import asyncio
import json
import logging
import time
import random
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from duckduckgo_search import DDGS
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CompanyInfo:
    """Data class for company information"""
    name: str
    industry: str
    description: str
    website: Optional[str] = None
    location: Optional[str] = None
    founded: Optional[str] = None
    employees: Optional[str] = None
    revenue: Optional[str] = None


class ModelAgent:
    """
    Model Agent that uses DuckDuckGo Chat to find companies in specific industries
    """
    
    def __init__(self, max_results: int = 10, region: str = "us-en", industry: str = None):
        """
        Initialize the Model Agent
        
        Args:
            max_results: Maximum number of results to return
            region: Region for search (default: us-en)
            industry: Industry for industry-specific configuration
        """
        self.max_results = max_results
        self.region = region
        self.industry = industry
        
        # Initialize DDGS with retry logic
        self.ddgs = None
        self._initialize_ddgs()
        
        # Rate limiting
        self.last_search_time = 0
        self.min_search_interval = 1.0  # Minimum seconds between searches

    def _initialize_ddgs(self):
        """Initialize DDGS with retry logic"""
        max_retries = 10
        for attempt in range(max_retries):
            try:
                self.ddgs = DDGS()
                logger.info("DDGS initialized successfully")
                return
            except Exception as e:
                logger.warning(f"DDGS initialization attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error("Failed to initialize DDGS after all retries")
                    raise

    def _rate_limit(self):
        """Implement rate limiting between searches"""
        current_time = time.time()
        time_since_last = current_time - self.last_search_time
        
        if time_since_last < self.min_search_interval:
            sleep_time = self.min_search_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_search_time = time.time()
        
    def get_system_prompt(self, industry: str) -> str:
        return f"""You are a business intelligence assistant specialized in finding and analyzing companies in specific industries. 

Your task is to find companies which specialization is in {industry} and provide comprehensive information about each company including:

1. Company name
2. Industry/sector
3. Brief description of what the company does
4. Website URL (if available)
5. Location/headquarters
6. Founded year (if available)
7. Number of employees (if available)
8. Annual revenue (if available)

Please provide the information in a structured format. Focus on well-known, established companies. If you cannot find specific details for some fields, indicate "Not available" rather than making up information.

Search for companies that are:
- Publicly traded or well-established private companies
- Actively operating in the {industry}

Provide up to {self.max_results} companies."""

    async def search_companies(self, industry: str, additional_context: str = "") -> List[CompanyInfo]:
        """
        Search for companies in a specific industry using DuckDuckGo Chat
        
        Args:
            industry: Target industry to search for
            additional_context: Additional context or specific requirements
            
        Returns:
            List of CompanyInfo objects
        """
        try:
            # Apply rate limiting
            self._rate_limit()
            
            # Construct the search query
            query = f"companies in {industry} industry"
            if additional_context:
                query += f" {additional_context}"
            
            logger.info(f"Searching for companies in {industry} industry")
            
            # Use industry-specific search templates if available
            search_queries = self._get_search_queries(industry, additional_context)
            
            all_results = []
            for search_query in search_queries:
                try:
                    # Add random delay to avoid rate limiting
                    time.sleep(random.uniform(0.5, 1.5))
                    
                    results = self.ddgs.text(
                        search_query,
                        max_results=10
                    )
                    print(results)
                    all_results.extend(results)
                    logger.debug(f"Found {len(results)} results for query: {search_query}")
                    
                except Exception as e:
                    logger.warning(f"Search failed for query '{search_query}': {e}")
                    continue
            
            # Process search results to extract company information
            # companies = self._extract_company_info(all_results, industry)
        
            # Remove duplicates and limit results
            # unique_companies = self._remove_duplicates(companies)
            # return unique_companies[:self.max_results]
            
        except Exception as e:
            logger.error(f"Error searching for companies: {e}")
            return []

    def _get_search_queries(self, industry: str, additional_context: str = "") -> List[str]:
        """Get search queries based on industry and context"""
        search_queries = []
        # search_queries.append(f"top alternative data providers for credit scoring in emerging markets")
        search_queries.append(f"companies using non-traditional data for credit risk assessment")
        # search_queries.append(f"startups combining telco, utility, and social data for credit scoring")
        # search_queries.append(f"AI fintech companies offering behavioral-based credit insights")
        # search_queries.append(f"alternative credit scoring platforms for unbanked or underbanked populations")
        # search_queries.append(f"data analytics startups providing credit risk models from digital footprint")
        # search_queries.append(f"credit intelligence solutions using alternative data sources")
        # search_queries.append(f"fintechs using smartphone data to assess borrower reliability")
        # search_queries.append(f"credit scoring API providers using non-financial data")
        # search_queries.append(f"companies providing alternative KYC or identity intelligence through data analytics")
        
        # Remove duplicates and limit to reasonable number
        unique_queries = list(dict.fromkeys(search_queries))  # Preserve order
        return unique_queries[:6]  # Limit to 6 queries max

    def _remove_duplicates(self, companies: List[CompanyInfo]) -> List[CompanyInfo]:
        """Remove duplicate companies based on name similarity"""
        unique_companies = []
        seen_names = set()
        
        for company in companies:
            # Normalize company name for comparison
            normalized_name = company.name.lower().strip()
            
            # Check if we've seen a similar name
            is_duplicate = False
            for seen_name in seen_names:
                if self._names_similar(normalized_name, seen_name):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_companies.append(company)
                seen_names.add(normalized_name)
        
        return unique_companies

    def _names_similar(self, name1: str, name2: str, threshold: float = 0.8) -> bool:
        """Check if two company names are similar"""
        # Simple similarity check based on common words
        words1 = set(name1.split())
        words2 = set(name2.split())
        
        if not words1 or not words2:
            return False
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        similarity = len(intersection) / len(union) if union else 0
        return similarity >= threshold

    def _clean_text(self, text: str) -> str:
        """Clean and decode text to handle encoding issues"""
        if not text:
            return ""
        
        try:
            # Ensure text is properly decoded
            if isinstance(text, bytes):
                text = text.decode('utf-8', errors='ignore')
            
            # Remove or replace problematic characters
            import re
            
            # Remove non-ASCII characters that might be causing issues
            text = re.sub(r'[^\x00-\x7F]+', ' ', text)
            
            # Clean up extra whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text
            
        except Exception as e:
            logger.warning(f"Error cleaning text: {e}")
            return str(text) if text else ""

    def _extract_company_info(self, search_results: List[Dict], industry: str) -> List[CompanyInfo]:
        """
        Extract company information from search results
        
        Args:
            search_results: Raw search results from DuckDuckGo
            industry: Target industry
            
        Returns:
            List of CompanyInfo objects
        """
        companies = []
        seen_companies = set()
        
        for result in search_results:
            try:
                title = result.get('title', '')
                body = result.get('body', '')
                url = result.get('href', '')
                
                # Extract company name from title (simple heuristic)
                company_name = self._extract_company_name(title, body)
                
                if company_name and company_name.lower() not in seen_companies:
                    seen_companies.add(company_name.lower())
                    
                    # Extract additional information
                    description = self._extract_description(body, title)
                    location = self._extract_location(body)
                    founded = self._extract_founded_year(body)
                    employees = self._extract_employee_count(body)
                    revenue = self._extract_revenue(body)
                    
                    company = CompanyInfo(
                        name=company_name,
                        industry=industry,
                        description=description,
                        website=url if self._is_valid_website(url) else None,
                        location=location,
                        founded=founded,
                        employees=employees,
                        revenue=revenue
                    )
                    
                    companies.append(company)
                    
            except Exception as e:
                logger.warning(f"Error processing search result: {e}")
                continue
        
        return companies

    def _extract_company_name(self, title: str, body: str) -> Optional[str]:
        """Extract company name from title and body"""
        # Clean and decode text properly
        title = self._clean_text(title)
        body = self._clean_text(body)
        
        # Simple heuristic to extract company names
        # Look for patterns like "Company Name - Description" or "Company Name | Description"
        title_parts = title.split(' - ')[0].split(' | ')[0].split(' | ')[0]
        
        # Remove common suffixes
        suffixes = ['Inc.', 'Corp.', 'LLC', 'Ltd.', 'Co.', 'Company', 'Corporation']
        for suffix in suffixes:
            if title_parts.endswith(suffix):
                return title_parts
        
        # If no clear pattern, return first part of title
        return title_parts.strip() if title_parts.strip() else None

    def _extract_description(self, body: str, title: str) -> str:
        """Extract company description from body text"""
        # Clean the text first
        body = self._clean_text(body)
        title = self._clean_text(title)
        
        # Use first sentence or first 200 characters
        sentences = body.split('. ')
        if sentences:
            description = sentences[0]
            if len(description) > 200:
                description = description[:200] + "..."
            return description
        return "Description not available"

    def _extract_location(self, body: str) -> Optional[str]:
        """Extract company location from body text"""
        # Clean the text first
        body = self._clean_text(body)
        
        # Look for common location patterns
        import re
        location_patterns = [
            r'headquartered in ([^,]+)',
            r'based in ([^,]+)',
            r'located in ([^,]+)',
            r'([A-Z][a-z]+ [A-Z][a-z]+), ([A-Z]{2})',
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                location = match.group(1) if len(match.groups()) == 1 else f"{match.group(1)}, {match.group(2)}"
                return self._clean_text(location)
        
        return None

    def _extract_founded_year(self, body: str) -> Optional[str]:
        """Extract founded year from body text"""
        # Clean the text first
        body = self._clean_text(body)
        
        import re
        founded_patterns = [
            r'founded in (\d{4})',
            r'established in (\d{4})',
            r'founded (\d{4})',
            r'(\d{4}) founded'
        ]
        
        for pattern in founded_patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                year = int(match.group(1))
                if 1800 <= year <= 2024:  # Reasonable year range
                    return str(year)
        
        return None

    def _extract_employee_count(self, body: str) -> Optional[str]:
        """Extract employee count from body text"""
        # Clean the text first
        body = self._clean_text(body)
        
        import re
        employee_patterns = [
            r'(\d+(?:,\d+)*)\s+employees',
            r'(\d+(?:,\d+)*)\s+staff',
            r'workforce of (\d+(?:,\d+)*)',
            r'(\d+(?:,\d+)*)\s+people'
        ]
        
        for pattern in employee_patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None

    def _extract_revenue(self, body: str) -> Optional[str]:
        """Extract revenue information from body text"""
        # Clean the text first
        body = self._clean_text(body)
        
        import re
        revenue_patterns = [
            r'revenue of \$(\d+(?:\.\d+)?[BMK]?)',
            r'\$(\d+(?:\.\d+)?[BMK]?)\s+revenue',
            r'annual revenue of \$(\d+(?:\.\d+)?[BMK]?)',
            r'(\d+(?:\.\d+)?[BMK]?)\s+billion'
        ]
        
        for pattern in revenue_patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                return f"${match.group(1)}"
        
        return None

    def _is_valid_website(self, url: str) -> bool:
        """Check if URL is a valid website"""
        if not url:
            return False
        
        # Simple validation
        return url.startswith(('http://', 'https://')) and '.' in url

    def format_results(self, companies: List[CompanyInfo]) -> str:
        """
        Format company results for display
        
        Args:
            companies: List of CompanyInfo objects
            
        Returns:
            Formatted string of results
        """
        if not companies:
            return "No companies found in the specified industry."
        
        result = f"Found {len(companies)} companies:\n\n"
        
        for i, company in enumerate(companies, 1):
            result += f"{i}. {company.name}\n"
            result += f"   Industry: {company.industry}\n"
            result += f"   Description: {company.description}\n"
            
            if company.website:
                result += f"   Website: {company.website}\n"
            if company.location:
                result += f"   Location: {company.location}\n"
            if company.founded:
                result += f"   Founded: {company.founded}\n"
            if company.employees:
                result += f"   Employees: {company.employees}\n"
            if company.revenue:
                result += f"   Revenue: {company.revenue}\n"
            
            result += "\n"
        
        return result

    def save_results(self, companies: List[CompanyInfo], filename: str = None) -> str:
        """
        Save company results to a JSON file
        
        Args:
            companies: List of CompanyInfo objects
            filename: Optional filename (default: auto-generated)
            
        Returns:
            Path to saved file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"companies_{timestamp}.json"
        
        # Convert to dictionary format
        data = []
        for company in companies:
            data.append({
                'name': company.name,
                'industry': company.industry,
                'description': company.description,
                'website': company.website,
                'location': company.location,
                'founded': company.founded,
                'employees': company.employees,
                'revenue': company.revenue
            })
        
        filepath = f"/Users/katerynahunko/business/insiderai/{filename}"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {filepath}")
        return filepath


# Example usage and testing
async def main():
    """Example usage of the ModelAgent"""
    agent = ModelAgent(max_results=5)
    
    # Example: Search for companies in the technology industry
    print("Searching for companies in the technology industry...")
    companies = await agent.search_companies("fintech")
    
    # Display results
    print(agent.format_results(companies))
    
    # Save results
    if companies:
        filepath = agent.save_results(companies)
        print(f"\nResults saved to: {filepath}")


if __name__ == "__main__":
    asyncio.run(main())

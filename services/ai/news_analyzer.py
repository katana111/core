"""
AI-powered news analysis using OpenRouter API (free tier with meta-llama models)
Analyzes press mentions for sentiment, key topics, and provides summaries
"""

import os
import json
import requests
from typing import Dict, Optional
from datetime import datetime


class NewsAnalyzer:
    """Analyze news articles using free AI models via OpenRouter"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize news analyzer with OpenRouter API
        
        Args:
            api_key: OpenRouter API key (or set OPENROUTER_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            print("Warning: OPENROUTER_API_KEY not set. Get free key at https://openrouter.ai/")
        
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        # Using Meta's Llama 3.2 3B Instruct (free tier)
        self.model = "meta-llama/llama-3.2-3b-instruct:free"
    
    def analyze_article(self, title: str, content: str, company_name: str) -> Dict:
        """
        Analyze a news article using AI
        
        Args:
            title: Article title
            content: Article content/snippet
            company_name: Name of the company mentioned
            
        Returns:
            Dictionary with analysis results including cleaned title and main idea
        """
        if not self.api_key:
            return self._fallback_analysis(title, content, company_name)
        
        try:
            # Create analysis prompt
            prompt = f"""Analyze this press mention about {company_name}:

Title: {title}
Content: {content}

First, determine if this article is relevant for business intelligence about {company_name}. Only consider articles that discuss:
- {company_name}'s goals, successes, failures
- {company_name}'s product releases or new features  
- {company_name}'s new contracts or partnerships
- Acquisitions or investments involving {company_name}
- {company_name}'s collaborations or strategic initiatives
- {company_name}'s financial results or funding
- {company_name}'s leadership changes or corporate strategy

If the article is NOT specifically relevant to {company_name} (general industry news, mentions {company_name} only in passing, etc.), respond with: {{"relevant": false, "reason": "brief explanation"}}

If the article IS relevant to {company_name}, provide a JSON response with:
1. relevant: true
2. title: Create a concise title that clearly shows how this relates to {company_name}. Format: "{company_name}: [action/achievement]" (e.g., "Seon: Closes $80M Series C Funding")
3. main_idea: Extract the main idea in exactly 2-3 clear sentences focusing specifically on what {company_name} is doing/achieving/experiencing
4. sentiment: One of: positive, negative, neutral, mixed (from {company_name}'s perspective)
5. sentiment_score: A number from -1.0 (very negative) to 1.0 (very positive) for {company_name}
6. key_topics: Array of 3-5 main business topics/themes specific to {company_name} (e.g., ["funding", "product launch", "partnership"])
7. analysis: 2-3 sentence analysis of what this business development means specifically for {company_name}
8. business_impact: One of: high, medium, low (based on strategic importance to {company_name})

Focus ONLY on information directly related to {company_name}. Ignore general industry context.
Respond ONLY with valid JSON, no other text."""

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/parsersvc",
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 600
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Extract JSON from response (handle markdown code blocks)
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0].strip()
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0].strip()
                
                analysis = json.loads(content)
                
                # Check if article is relevant for business intelligence
                if not analysis.get('relevant', True):
                    return {
                        'relevant': False,
                        'reason': analysis.get('reason', 'Not business-relevant'),
                        'title': title,
                        'sentiment': 'neutral',
                        'sentiment_score': 0.0
                    }
                
                # Validate and normalize
                return {
                    'relevant': True,
                    'title': analysis.get('title', title)[:255],
                    'main_idea': analysis.get('main_idea', '')[:1000],
                    'sentiment': analysis.get('sentiment', 'neutral').lower(),
                    'sentiment_score': float(analysis.get('sentiment_score', 0.0)),
                    'key_topics': analysis.get('key_topics', [])[:10],
                    'analysis': analysis.get('analysis', '')[:1000],
                    'business_impact': analysis.get('business_impact', 'medium').lower()
                }
            else:
                print(f"API error: {response.status_code} - {response.text}")
                return self._fallback_analysis(title, content, company_name)
                
        except Exception as e:
            print(f"Error in AI analysis: {str(e)}")
            return self._fallback_analysis(title, content, company_name)
    
    def _fallback_analysis(self, title: str, content: str, company_name: str) -> Dict:
        """
        Simple rule-based analysis when AI is not available
        
        Args:
            title: Article title
            content: Article content
            company_name: Name of the company
            
        Returns:
            Basic analysis dictionary with relevance check
        """
        text = f"{title} {content}".lower()
        
        # Check for business relevance using keywords
        business_keywords = [
            # Company developments
            'funding', 'investment', 'series', 'raised', 'million', 'billion',
            'acquisition', 'acquired', 'merger', 'bought', 'purchase',
            'partnership', 'collaboration', 'alliance', 'agreement', 'contract',
            'launch', 'released', 'announced', 'unveil', 'introduce',
            'expansion', 'growth', 'new market', 'international',
            
            # Business results
            'revenue', 'profit', 'loss', 'earnings', 'financial results',
            'ipo', 'public', 'listing', 'stock', 'shares',
            'ceo', 'cto', 'cfo', 'executive', 'leadership', 'appointed', 'hired',
            'strategy', 'roadmap', 'vision', 'goals', 'objectives',
            
            # Product/tech developments  
            'product', 'feature', 'update', 'version', 'platform',
            'technology', 'innovation', 'patent', 'breakthrough',
            'customer', 'client', 'user', 'adoption', 'deployment'
        ]
        
        # Check if article contains business-relevant content
        relevance_score = sum(1 for keyword in business_keywords if keyword in text)
        
        # Filter out clearly irrelevant content
        irrelevant_indicators = [
            'event', 'conference', 'webinar', 'speaking at', 'will speak',
            'opinion', 'commentary', 'analysis by', 'expert says',
            'industry report', 'market research', 'survey finds',
            'general', 'overall', 'market trends', 'industry trends'
        ]
        
        irrelevance_score = sum(1 for indicator in irrelevant_indicators if indicator in text)
        
        # Determine relevance
        if relevance_score < 2 or irrelevance_score > relevance_score:
            return {
                'relevant': False,
                'reason': f'Low business relevance (score: {relevance_score}, irrelevance: {irrelevance_score})',
                'title': title,
                'sentiment': 'neutral',
                'sentiment_score': 0.0
            }
        
        # Clean title - if longer than one sentence, take first sentence
        cleaned_title = title
        if '. ' in title:
            sentences = title.split('. ')
            if len(sentences[0]) > 20:  # First sentence is substantial
                cleaned_title = sentences[0] + '.'
        
        # Extract main idea - take first 2-3 sentences from content or title+content
        full_text = f"{title} {content}"
        sentences = full_text.split('. ')
        main_idea_sentences = []
        for sent in sentences[:3]:
            if sent.strip() and len(sent.strip()) > 20:
                main_idea_sentences.append(sent.strip())
                if len(main_idea_sentences) >= 2:
                    break
        
        main_idea = '. '.join(main_idea_sentences)
        if main_idea and not main_idea.endswith('.'):
            main_idea += '.'
        
        # Simple sentiment analysis
        positive_words = ['growth', 'success', 'launch', 'raise', 'funding', 'partnership', 
                         'expansion', 'innovative', 'award', 'leading', 'breakthrough']
        negative_words = ['lawsuit', 'breach', 'hack', 'loss', 'decline', 'failure', 
                         'shutdown', 'layoff', 'scandal', 'fine', 'investigation']
        
        pos_count = sum(1 for word in positive_words if word in text)
        neg_count = sum(1 for word in negative_words if word in text)
        
        if pos_count > neg_count:
            sentiment = 'positive'
            sentiment_score = min(0.8, pos_count * 0.2)
        elif neg_count > pos_count:
            sentiment = 'negative'
            sentiment_score = max(-0.8, -neg_count * 0.2)
        else:
            sentiment = 'neutral'
            sentiment_score = 0.0
        
        # Extract basic topics
        topics = []
        topic_keywords = {
            'funding': ['funding', 'raise', 'investment', 'series', 'capital'],
            'product': ['launch', 'product', 'feature', 'release', 'announce'],
            'partnership': ['partnership', 'partner', 'collaborate', 'agreement'],
            'expansion': ['expansion', 'growth', 'enter', 'market', 'expand'],
            'acquisition': ['acquire', 'acquisition', 'merger', 'buy']
        }
        
        for topic, keywords in topic_keywords.items():
            if any(kw in text for kw in keywords):
                topics.append(topic)
        
        return {
            'relevant': True,
            'title': cleaned_title[:255],
            'main_idea': main_idea[:1000] if main_idea else title[:200],
            'sentiment': sentiment,
            'sentiment_score': sentiment_score,
            'key_topics': topics[:5] if topics else ['general'],
            'analysis': f"Press mention detected with {sentiment} sentiment based on keyword analysis.",
            'business_impact': 'medium' if pos_count > 0 or neg_count > 0 else 'low'
        }
    
    def analyze_batch(self, articles: list, company_name: str) -> list:
        """
        Analyze multiple articles
        
        Args:
            articles: List of article dictionaries
            company_name: Company name
            
        Returns:
            List of analysis results
        """
        results = []
        for article in articles:
            analysis = self.analyze_article(
                article.get('title', ''),
                article.get('content', ''),
                company_name
            )
            analysis['article'] = article
            results.append(analysis)
        
        return results

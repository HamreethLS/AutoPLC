# backend/tools/retrieval_tools.py
import os
import requests
from dotenv import load_dotenv
import asyncio
from playwright.async_api import async_playwright
from typing import Dict, List, Optional
import json
import re

load_dotenv()

class EnhancedRetrievalTools:
    """Enhanced retrieval tools with better error handling and caching."""
    
    def __init__(self):
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        self.cache = {}  # Simple in-memory cache
        
    def search_tavily(self, query: str, max_results: int = 3) -> str:
        """Enhanced Tavily search with better result formatting."""
        
        if not self.tavily_api_key:
            return "⚠️  Tavily API key not configured. External search unavailable."
        
        # Check cache first
        cache_key = f"tavily_{query}_{max_results}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.tavily_api_key,
                    "query": query,
                    "search_depth": "advanced",  # Enhanced search depth
                    "include_answer": True,
                    "include_raw_content": False,
                    "max_results": max_results,
                    "include_domains": [],
                    "exclude_domains": ["reddit.com", "stackoverflow.com"]  # Filter out forums
                },
                timeout=15
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Enhanced result formatting
            formatted_result = self._format_tavily_results(result)
            
            # Cache the result
            self.cache[cache_key] = formatted_result
            
            return formatted_result
            
        except requests.exceptions.RequestException as e:
            return f"🔍 Tavily Search Error: {str(e)}"
        except Exception as e:
            return f"🔍 Search processing error: {str(e)}"
    
    def _format_tavily_results(self, result: Dict) -> str:
        """Format Tavily search results for better readability."""
        
        output_lines = ["🔍 External Search Results:"]
        
        # Include direct answer if available
        if "answer" in result and result["answer"]:
            output_lines.append(f"\n📋 Summary: {result['answer']}")
            output_lines.append("\n" + "─" * 40)
        
        # Process search results
        results = result.get("results", [])
        if results:
            output_lines.append("\n📖 Detailed Sources:")
            
            for i, res in enumerate(results, 1):
                title = res.get('title', 'Untitled')
                snippet = res.get('snippet', 'No description')
                url = res.get('url', '')
                
                # Clean up title and snippet
                title = re.sub(r'[^\w\s\-\.]', '', title)[:100]
                snippet = re.sub(r'[^\w\s\-\.,]', '', snippet)[:200]
                
                output_lines.append(f"\n{i}. **{title}**")
                output_lines.append(f"   {snippet}")
                if url:
                    output_lines.append(f"   🔗 {url}")
        
        return "\n".join(output_lines) if len(output_lines) > 1 else "🔍 No relevant external results found."

# Enhanced async scraping functions
async def _scrape_url_enhanced(url: str) -> Dict:
    """Enhanced async URL scraping with better content extraction."""
    
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Enhanced navigation with better error handling
            await page.goto(url, wait_until="networkidle", timeout=20000)
            
            # Wait for dynamic content
            await page.wait_for_timeout(2000)
            
            # Extract structured content
            content_data = await page.evaluate("""
                () => {
                    // Remove scripts, styles, and navigation
                    const elementsToRemove = document.querySelectorAll('script, style, nav, footer, header, .sidebar');
                    elementsToRemove.forEach(el => el.remove());
                    
                    // Get main content
                    const mainContent = document.querySelector('main, .main, .content, article') || document.body;
                    
                    return {
                        title: document.title,
                        text: mainContent.innerText,
                        headings: Array.from(document.querySelectorAll('h1, h2, h3')).map(h => h.innerText),
                        url: window.location.href
                    };
                }
            """)
            
            await browser.close()
            
            # Clean and process content
            cleaned_text = _clean_scraped_text(content_data['text'])
            
            return {
                "success": True,
                "title": content_data['title'][:200],
                "content": cleaned_text[:5000],  # Increased limit
                "headings": content_data['headings'][:10],
                "url": content_data['url']
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": "",
                "title": "",
                "headings": [],
                "url": url
            }

def _clean_scraped_text(text: str) -> str:
    """Clean scraped text for better processing."""
    
    if not text:
        return ""
    
    # Remove excessive whitespace
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Filter out navigation, cookie notices, etc.
    filtered_lines = []
    skip_patterns = [
        r"cookie", r"privacy policy", r"subscribe", r"newsletter", 
        r"follow us", r"social media", r"advertisement"
    ]
    
    for line in lines:
        if len(line) > 20 and not any(re.search(pattern, line, re.IGNORECASE) for pattern in skip_patterns):
            filtered_lines.append(line)
    
    return '\n'.join(filtered_lines)

def scrape_with_playwright(url: str) -> str:
    """Enhanced Playwright scraping with structured output."""
    
    if not url.startswith(('http://', 'https://')):
        return "❌ Invalid URL format. URL must start with http:// or https://"
    
    try:
        # Run the async scraping
        result = asyncio.run(_scrape_url_enhanced(url))
        
        if result["success"]:
            # Format the scraped content
            output_lines = [
                f"🌐 Scraped Content from: {result['url']}",
                f"📄 Title: {result['title']}",
                "─" * 50
            ]
            
            if result['headings']:
                output_lines.append("📑 Key Sections:")
                for heading in result['headings']:
                    output_lines.append(f"   • {heading}")
                output_lines.append("─" * 30)
            
            output_lines.append("📖 Content:")
            output_lines.append(result['content'])
            
            return "\n".join(output_lines)
        else:
            return f"❌ Scraping failed for {url}: {result['error']}"
            
    except Exception as e:
        return f"❌ Playwright scraping error: {str(e)}"

# Global instances for backward compatibility
enhanced_retrieval = EnhancedRetrievalTools()

def search_tavily(query: str) -> str:
    """Backward compatible function."""
    return enhanced_retrieval.search_tavily(query)

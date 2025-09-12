"""
Enhanced Retrieval Agent with intelligent search and result processing
"""

import asyncio
from typing import Dict, List, Optional, Any

from backend.tools.retrieval_tools import enhanced_retrieval
from backend.utils.nim_client import enhanced_nim_client

class RetrievalAgent:
    """Enhanced retrieval agent with context-aware external search"""
    
    def __init__(self):
        self.search_strategies = {
            "hardware": self._get_hardware_strategy(),
            "protocol": self._get_protocol_strategy(), 
            "standard": self._get_standard_strategy(),
            "troubleshooting": self._get_troubleshooting_strategy(),
            "general": self._get_general_strategy()
        }
        
        self.result_cache = {}
    
    async def search_external(self, query: str, context: Optional[Dict] = None) -> str:
        """Perform intelligent external search with result synthesis"""
        
        # Check cache first
        cache_key = f"{query}_{hash(str(context) if context else '')}"
        if cache_key in self.result_cache:
            return self.result_cache[cache_key]
        
        # Determine search strategy
        search_type = self._classify_search_need(query, context)
        strategy = self.search_strategies[search_type]
        
        try:
            # Enhance query for better results
            enhanced_queries = self._generate_search_queries(query, search_type)
            
            # Perform searches
            search_results = []
            for search_query in enhanced_queries:
                result = enhanced_retrieval.search_tavily(search_query, max_results=2)
                if result and "error" not in result.lower():
                    search_results.append(result)
            
            # Process and synthesize results
            if search_results:
                synthesized_result = await self._synthesize_results(
                    search_results, query, search_type
                )
                
                # Cache the result
                self.result_cache[cache_key] = synthesized_result
                return synthesized_result
            else:
                return self._provide_fallback_info(query, search_type)
                
        except Exception as e:
            return f"External search error: {str(e)}. Using general guidance for {query}."
    
    def _classify_search_need(self, query: str, context: Optional[Dict]) -> str:
        """Classify what type of external information is needed"""
        
        query_lower = query.lower()
        
        # Hardware-specific search
        hardware_indicators = [
            "model", "specification", "datasheet", "manual", "wiring", 
            "i/o", "modules", "cpu", "plc", "hmi"
        ]
        if any(indicator in query_lower for indicator in hardware_indicators):
            return "hardware"
        
        # Protocol/communication search
        protocol_indicators = [
            "modbus", "profinet", "ethernet/ip", "profibus", "can", 
            "protocol", "communication", "network", "tcp", "serial"
        ]
        if any(indicator in query_lower for indicator in protocol_indicators):
            return "protocol"
        
        # Standards search
        standard_indicators = [
            "iec", "61131", "61508", "standard", "compliance", "safety", 
            "certification", "iso", "ansi"
        ]
        if any(indicator in query_lower for indicator in standard_indicators):
            return "standard"
        
        # Troubleshooting search
        trouble_indicators = [
            "error", "fault", "troubleshoot", "debug", "problem", "issue",
            "not working", "failed", "alarm"
        ]
        if any(indicator in query_lower for indicator in trouble_indicators):
            return "troubleshooting"
        
        return "general"
    
    def _generate_search_queries(self, original_query: str, search_type: str) -> List[str]:
        """Generate optimized search queries for different types"""
        
        base_query = original_query
        
        if search_type == "hardware":
            return [
                f"{base_query} specification datasheet",
                f"{base_query} manual wiring diagram",
                f"{base_query} programming guide"
            ]
        
        elif search_type == "protocol":
            return [
                f"{base_query} implementation guide",
                f"{base_query} configuration setup",
                f"{base_query} programming example"
            ]
        
        elif search_type == "standard":
            return [
                f"{base_query} IEC 61131-3 compliance",
                f"{base_query} standard requirements",
                f"{base_query} best practices"
            ]
        
        elif search_type == "troubleshooting":
            return [
                f"{base_query} troubleshooting guide",
                f"{base_query} common problems solutions",
                f"{base_query} error codes meaning"
            ]
        
        else:  # general
            return [
                f"{base_query} industrial automation",
                f"{base_query} PLC programming guide"
            ][:2]  # Limit to 2 queries for general searches
    
    async def _synthesize_results(
        self, 
        search_results: List[str], 
        original_query: str,
        search_type: str
    ) -> str:
        """Synthesize search results into useful information"""
        
        # Combine all search results
        combined_results = "\n\n".join(search_results)
        
        # Use AI to synthesize the information
        synthesis_prompt = f"""
You are a technical expert synthesizing research information for PLC programming.

ORIGINAL QUERY: {original_query}
SEARCH TYPE: {search_type}

SEARCH RESULTS:
{combined_results}

Please synthesize this information into:
1. Key technical specifications or requirements
2. Relevant programming considerations
3. Important configuration details
4. Safety or compliance notes if applicable

Focus on practical information useful for PLC programming. Be concise but thorough.

Synthesis:"""
        
        try:
            synthesized = await enhanced_nim_client.call_agent_simple(
                agent_role="retriever",
                prompt=synthesis_prompt,
                temperature=0.2,
                max_tokens=1000
            )
            
            return f"External Research Results:\n{synthesized}"
            
        except Exception as e:
            # Fall back to raw results if synthesis fails
            return f"External Research Results:\n{combined_results[:2000]}..."
    
    def _provide_fallback_info(self, query: str, search_type: str) -> str:
        """Provide fallback information when external search fails"""
        
        fallback_info = {
            "hardware": f"""
Hardware Research - {query}:
• Consult manufacturer documentation for specific I/O addressing
• Verify power requirements and wiring specifications  
• Check compatibility with IEC 61131-3 programming standards
• Ensure proper grounding and safety considerations
• Reference installation and maintenance manuals
""",
            "protocol": f"""
Communication Protocol - {query}:
• Verify protocol specifications and data formats
• Check baud rate, parity, and stop bit configurations
• Ensure proper cable types and connection methods
• Implement error handling and timeout mechanisms
• Test communication reliability before deployment
""",
            "standard": f"""
Standards Compliance - {query}:
• Follow IEC 61131-3 programming language standards
• Implement safety functions per IEC 61508 if applicable
• Use standard data types and addressing conventions
• Include proper documentation and commenting
• Validate code through proper testing procedures
""",
            "troubleshooting": f"""
Troubleshooting Guide - {query}:
• Check physical connections and wiring
• Verify power supply voltages and stability
• Review program logic for proper sequencing
• Test I/O functionality independently
• Monitor system diagnostics and error logs
""",
            "general": f"""
General Information - {query}:
• Apply industrial automation best practices
• Follow manufacturer guidelines and standards
• Implement proper error handling and safety measures
• Test thoroughly before production deployment
• Maintain detailed documentation for future reference
"""
        }
        
        return fallback_info.get(search_type, fallback_info["general"])
    
    def _get_hardware_strategy(self) -> Dict[str, Any]:
        return {
            "focus": "specifications, manuals, datasheets",
            "sources": ["manufacturer sites", "technical documentation"],
            "keywords": ["specification", "manual", "datasheet", "wiring"]
        }
    
    def _get_protocol_strategy(self) -> Dict[str, Any]:
        return {
            "focus": "implementation guides, configuration",
            "sources": ["protocol standards", "implementation guides"],
            "keywords": ["implementation", "configuration", "setup"]
        }
    
    def _get_standard_strategy(self) -> Dict[str, Any]:
        return {
            "focus": "compliance requirements, best practices",
            "sources": ["standards organizations", "compliance guides"],
            "keywords": ["standard", "compliance", "requirements"]
        }
    
    def _get_troubleshooting_strategy(self) -> Dict[str, Any]:
        return {
            "focus": "problem resolution, diagnostics",
            "sources": ["troubleshooting guides", "support forums"],
            "keywords": ["troubleshooting", "problem", "solution", "fix"]
        }
    
    def _get_general_strategy(self) -> Dict[str, Any]:
        return {
            "focus": "general information, best practices",
            "sources": ["technical documentation", "programming guides"],
            "keywords": ["guide", "tutorial", "best practices"]
        }
    
    async def get_hardware_specifications(self, hardware_model: str) -> str:
        """Get specific hardware specifications"""
        query = f"{hardware_model} specifications I/O modules addressing"
        return await self.search_external(query, {"type": "hardware_spec"})
    
    async def get_protocol_info(self, protocol_name: str) -> str:
        """Get protocol implementation information"""
        query = f"{protocol_name} PLC implementation configuration"
        return await self.search_external(query, {"type": "protocol_info"})
    
    def clear_cache(self):
        """Clear the result cache"""
        self.result_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cached_results": len(self.result_cache),
            "search_strategies": list(self.search_strategies.keys())
        }

"""
Enhanced Knowledge Agent with intelligent query processing and caching
"""

import asyncio
from typing import Dict, List, Optional, Any

from backend.tools.knowledge_base import query_knowledge_base, search_knowledge_base
from backend.utils.nim_client import enhanced_nim_client

class KnowledgeAgent:
    """Enhanced knowledge agent with context-aware querying and result synthesis"""
    
    def __init__(self):
        self.query_cache = {}
        self.specialization_keywords = {
            "syntax": ["comment", "declaration", "variable", "operator", "expression"],
            "data_types": ["bool", "int", "real", "string", "time", "byte", "word"],
            "structure": ["program", "function", "block", "var", "begin", "end"],
            "timing": ["timer", "delay", "timeout", "cycle", "scan"],
            "safety": ["emergency", "interlock", "fail-safe", "alarm", "stop"],
            "communication": ["modbus", "ethernet", "profinet", "protocol", "network"]
        }
    
    async def query_knowledge(self, query: str, context: Optional[Dict] = None) -> str:
        """Enhanced knowledge querying with context awareness"""
        
        # Check cache first
        cache_key = self._generate_cache_key(query, context)
        if cache_key in self.query_cache:
            return self.query_cache[cache_key]
        
        # Enhance query based on context
        enhanced_query = self._enhance_query(query, context)
        
        # Get specialized knowledge
        knowledge_type = self._classify_query(enhanced_query)
        
        try:
            # Query the knowledge base
            raw_results = query_knowledge_base(enhanced_query, max_results=5)
            
            # If insufficient results, try broader queries
            if "No relevant information" in raw_results:
                broader_query = self._create_broader_query(query)
                raw_results = query_knowledge_base(broader_query, max_results=3)
            
            # Process and synthesize results
            processed_result = await self._process_knowledge_results(
                raw_results, query, knowledge_type
            )
            
            # Cache the result
            self.query_cache[cache_key] = processed_result
            
            return processed_result
            
        except Exception as e:
            return f"Knowledge query error: {str(e)}. Using fallback knowledge for IEC 61131-3 programming."
    
    def _enhance_query(self, query: str, context: Optional[Dict]) -> str:
        """Enhance the query with context information"""
        
        enhanced_parts = [query]
        
        if context:
            # Add context from previous agents
            if "original_prompt" in context:
                enhanced_parts.append(f"Context: {context['original_prompt']}")
            
            # Add hardware context if available
            if "hardware" in context:
                enhanced_parts.append(f"Hardware: {context['hardware']}")
        
        return " ".join(enhanced_parts)
    
    def _classify_query(self, query: str) -> str:
        """Classify the query to determine knowledge specialization needed"""
        
        query_lower = query.lower()
        
        for category, keywords in self.specialization_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return category
        
        return "general"
    
    def _create_broader_query(self, original_query: str) -> str:
        """Create a broader query if the original doesn't yield results"""
        
        # Extract key technical terms
        technical_terms = []
        query_words = original_query.lower().split()
        
        iec_terms = [
            "structured text", "ladder", "function block", "variable", "program",
            "timer", "counter", "bool", "int", "real", "communication"
        ]
        
        for term in iec_terms:
            if any(word in term for word in query_words):
                technical_terms.append(term)
        
        if technical_terms:
            return f"IEC 61131-3 programming {' '.join(technical_terms[:2])}"
        else:
            return "IEC 61131-3 structured text programming basics"
    
    async def _process_knowledge_results(
        self, 
        raw_results: str, 
        original_query: str,
        knowledge_type: str
    ) -> str:
        """Process and synthesize knowledge results using AI"""
        
        if "No relevant information" in raw_results:
            return await self._provide_fallback_knowledge(original_query, knowledge_type)
        
        # Use AI to synthesize and clarify the knowledge
        synthesis_prompt = f"""
You are an IEC 61131-3 expert. Synthesize the following raw knowledge into a concise list of rules and constraints relevant to the user's query.

ORIGINAL QUERY: {original_query}
KNOWLEDGE TYPE: {knowledge_type}

RAW KNOWLEDGE:
{raw_results}

**Instructions:**
1.  **Extract Key Rules:** Identify the most critical IEC 61131-3 rules, syntax, and best practices from the raw knowledge.
2.  **Be Concise:** Use bullet points or a numbered list.
3.  **Focus on Constraints:** Output facts and constraints that a planner and coder must follow.
4.  **DO NOT** include conversational text, greetings, or full code examples. Just provide the synthesized facts.

**Synthesized Knowledge (Facts & Rules Only):**
"""
        
        try:
            synthesized = await enhanced_nim_client.call_agent_simple(
                agent_role="knowledge",
                prompt=synthesis_prompt,
                temperature=0.0,
                max_tokens=600
            )
            
            return f"IEC 61131-3 Knowledge:\n{synthesized}"
            
        except Exception as e:
            # Fall back to raw results if synthesis fails
            return raw_results
    
    async def _provide_fallback_knowledge(self, query: str, knowledge_type: str) -> str:
        """Provide fallback knowledge when database query fails"""
        
        fallback_knowledge = {
            "syntax": """
IEC 61131-3 Structured Text Syntax Rules:
• Comments: Use (* comment *) syntax only
• Variable declarations: VAR variable_name : DATA_TYPE := initial_value; END_VAR
• Assignments: variable := expression;
• Conditionals: IF condition THEN statements; END_IF;
• All executable code must be between BEGIN and END_PROGRAM
""",
            "data_types": """
Standard IEC 61131-3 Data Types:
• BOOL: TRUE/FALSE values
• INT: Integer numbers (-32768 to 32767)
• REAL: Floating point numbers
• STRING: Text strings
• TIME: Duration values (T#1s, T#100ms)
• Variable addressing: AT %I0.0 (input), AT %Q0.0 (output)
""",
            "structure": """
IEC 61131-3 Program Structure:
PROGRAM ProgramName
VAR
    (* Variable declarations *)
END_VAR

BEGIN
    (* Executable logic *)
END_PROGRAM
""",
            "timing": """
Timer Implementation in IEC 61131-3:
• Avoid TON/TOF function blocks if not available
• Use TIME variables and manual timing logic
• Example: IF timer_start THEN start_time := CURRENT_TIME; END_IF;
• Check elapsed time: IF (CURRENT_TIME - start_time) >= delay_time THEN ...
""",
            "safety": """
Safety Programming in IEC 61131-3:
• Always implement emergency stop checks first
• Use fail-safe logic (default to safe state)
• Validate inputs before using them
• Example: IF NOT emergency_stop AND input_valid THEN output := TRUE; END_IF;
""",
            "general": """
IEC 61131-3 Programming Best Practices:
• Use descriptive variable names
• Include comments for complex logic
• Declare all variables before use
• Avoid complex nesting (max 3 levels)
• Test logic with static values first
• Follow scan cycle principles
"""
        }
        
        return fallback_knowledge.get(knowledge_type, fallback_knowledge["general"])
    
    def _generate_cache_key(self, query: str, context: Optional[Dict]) -> str:
        """Generate a cache key for the query"""
        context_str = str(sorted(context.items())) if context else ""
        return f"{query}_{hash(context_str)}"
    
    async def get_specialized_knowledge(self, topic: str, complexity_level: str = "basic") -> str:
        """Get specialized knowledge for specific topics"""
        
        specialized_queries = {
            "motor_control": "motor control start stop latch logic IEC 61131-3",
            "conveyor_systems": "conveyor belt control direction speed safety",
            "safety_systems": "emergency stop safety interlock fail-safe logic",
            "timing_control": "timer delay timing control without TON function blocks",
            "sequential_control": "sequential step control state machine CASE statement"
        }
        
        query = specialized_queries.get(topic, f"{topic} IEC 61131-3 programming")
        return await self.query_knowledge(query)
    
    def clear_cache(self):
        """Clear the query cache"""
        self.query_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cached_queries": len(self.query_cache),
            "specializations": list(self.specialization_keywords.keys())
        }

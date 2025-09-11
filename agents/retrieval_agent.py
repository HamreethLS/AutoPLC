"""Retrieval agent for PLC domain knowledge using RAG."""

import logging
from typing import Dict, Any, List
from datetime import datetime

from agents.base_agent import LLMAgent
from models.schemas import AgentRole, AgentTask
from knowledge.rag_system import PLCKnowledgeBase, RAGRetriever


class RetrievalAgent(LLMAgent):
    """Agent responsible for retrieving relevant PLC domain knowledge."""
    
    def __init__(self, llm=None):
        super().__init__(
            role=AgentRole.RETRIEVAL,
            name="PLC Knowledge Retriever",
            description="Retrieves relevant PLC programming knowledge and examples using RAG",
            llm=llm
        )
        
        # Initialize knowledge base and RAG system
        self.knowledge_base = PLCKnowledgeBase()
        self.rag_retriever = RAGRetriever(self.knowledge_base)
        
        # Load knowledge documents on initialization
        self._initialize_knowledge()
    
    def _initialize_knowledge(self):
        """Initialize the knowledge base with PLC domain knowledge."""
        try:
            # Load existing knowledge or create sample documents
            self.knowledge_base.load_knowledge_documents()
            
            # Get knowledge base stats
            stats = self.knowledge_base.get_stats()
            self.logger.info(f"Knowledge base initialized: {stats}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize knowledge base: {str(e)}")
            raise
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the retrieval agent."""
        return """
You are a PLC Knowledge Retrieval Agent specialized in IEC 61131-3 programming standards.

Your responsibilities:
1. Retrieve relevant PLC programming knowledge based on user requirements
2. Find appropriate code examples and patterns
3. Provide safety guidelines and best practices
4. Extract domain-specific information for code generation

You have access to a comprehensive knowledge base containing:
- IEC 61131-3 programming language specifications
- Structured Text (ST) syntax and examples
- Safety programming guidelines (SIL levels)
- Common PLC programming patterns
- Function block libraries and usage

When retrieving knowledge:
- Focus on relevance to the specific requirement
- Include safety considerations when applicable
- Provide concrete examples when available
- Consider the target safety integrity level (SIL)
- Extract both theoretical knowledge and practical patterns

Always prioritize safety and compliance with industrial standards.
"""
    
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        """Process a knowledge retrieval task."""
        task_type = task.task_type
        input_data = task.input_data
        
        if task_type == "retrieve_knowledge":
            return await self._retrieve_knowledge(input_data)
        elif task_type == "find_examples":
            return await self._find_examples(input_data)
        elif task_type == "get_safety_guidelines":
            return await self._get_safety_guidelines(input_data)
        elif task_type == "search_patterns":
            return await self._search_patterns(input_data)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _retrieve_knowledge(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve general knowledge based on requirements."""
        requirement = input_data.get("requirement", {})
        
        # Extract key information from requirement
        description = requirement.get("description", "")
        language = requirement.get("language", "st")
        safety_level = requirement.get("safety_level", 1)
        
        # Build search query
        search_query = f"{description} {language} programming"
        
        # Retrieve relevant context
        context = self.rag_retriever.retrieve_context(search_query, max_chunks=5)
        
        # Get safety guidelines if safety level > 1
        safety_context = ""
        if safety_level > 1:
            safety_context = self.rag_retriever.retrieve_safety_guidelines(safety_level)
        
        # Get relevant examples
        examples = self.rag_retriever.retrieve_examples("general", language.upper())
        
        return {
            "context": context,
            "safety_guidelines": safety_context,
            "examples": examples,
            "search_query": search_query,
            "retrieved_at": datetime.utcnow().isoformat()
        }
    
    async def _find_examples(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Find specific code examples for a task."""
        task_description = input_data.get("task_description", "")
        language = input_data.get("language", "ST")
        pattern_type = input_data.get("pattern_type", "general")
        
        # Search for examples
        examples = self.rag_retriever.retrieve_examples(pattern_type, language)
        
        # If no specific examples found, search more broadly
        if not examples:
            search_query = f"{task_description} {language} code example"
            results = self.knowledge_base.search_knowledge(search_query, k=3)
            examples = [doc.page_content for doc in results]
        
        return {
            "examples": examples,
            "pattern_type": pattern_type,
            "language": language,
            "search_performed": task_description
        }
    
    async def _get_safety_guidelines(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve safety programming guidelines."""
        safety_level = input_data.get("safety_level", 1)
        application_type = input_data.get("application_type", "general")
        
        # Get safety guidelines
        guidelines = self.rag_retriever.retrieve_safety_guidelines(safety_level)
        
        # Search for application-specific safety information
        if application_type != "general":
            search_query = f"safety {application_type} programming guidelines"
            results = self.knowledge_base.search_knowledge(search_query, k=2)
            app_specific = [doc.page_content for doc in results]
        else:
            app_specific = []
        
        return {
            "general_guidelines": guidelines,
            "application_specific": app_specific,
            "safety_level": safety_level,
            "application_type": application_type
        }
    
    async def _search_patterns(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Search for specific programming patterns."""
        pattern_name = input_data.get("pattern_name", "")
        context = input_data.get("context", "")
        
        # Build search query
        search_query = f"{pattern_name} pattern {context}"
        
        # Search for patterns
        results = self.knowledge_base.search_with_score(search_query, k=5)
        
        patterns = []
        for doc, score in results:
            if score < 0.7:  # High relevance threshold
                patterns.append({
                    "content": doc.page_content,
                    "relevance": 1 - score,
                    "metadata": doc.metadata
                })
        
        return {
            "patterns": patterns,
            "search_query": search_query,
            "total_found": len(patterns)
        }
    
    def add_knowledge(self, content: str, metadata: Dict[str, Any] = None):
        """Add new knowledge to the knowledge base."""
        self.knowledge_base.add_knowledge(content, metadata)
        self.logger.info("Added new knowledge to the knowledge base")
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base."""
        return self.knowledge_base.get_stats()
    
    async def receive_message(self, message) -> Dict[str, Any]:
        """Handle messages from other agents."""
        content = message.content
        
        if content.get("type") == "knowledge_request":
            # Handle direct knowledge requests from other agents
            query = content.get("query", "")
            context = self.rag_retriever.retrieve_context(query)
            
            return {
                "type": "knowledge_response",
                "context": context,
                "query": query
            }
        
        return await super().receive_message(message)

# backend/utils/nim_client.py
import os
import requests
import json
import random
import time
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class EnhancedNIMClient:
    """
    Enhanced NVIDIA NIM API client with intelligent dual-key routing
    """
    
    def __init__(self):
        # Dual API key setup
        self.api_keys = {
            "primary": os.getenv("NVIDIA_API_KEY_1"),
            "secondary": os.getenv("NVIDIA_API_KEY_2")
        }
        
        self.base_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        
        # Key assignment strategy for optimal load distribution
        self.key_assignments = {
            # Heavy reasoning models get dedicated keys
            "planner": "primary",      # Llama 3.1-70B on primary key
            "coder": "secondary",      # Llama 3.1-70B on secondary key
            
            # Light models share secondary key with load balancing
            "validator": "auto",       # Mistral-7B with auto selection
            "retriever": "auto",       # Mistral-7B with auto selection  
            "knowledge": "auto",       # Phi-4-Mini with auto selection
            "fallback": "auto"
        }
        
        # Enhanced model mapping with token optimization
        self.model_map = {
            "planner": "meta/llama-3.1-70b-instruct",
            "coder": "meta/llama-3.1-70b-instruct", 
            "validator": "mistralai/mistral-7b-instruct-v0.3",
            "retriever": "mistralai/mistral-7b-instruct-v0.3",
            "knowledge": "microsoft/phi-4-mini-instruct",
            "fallback": "microsoft/phi-4-mini-instruct"
        }
        
        # Performance tracking for intelligent routing
        self.key_performance = {
            "primary": {"requests": 0, "failures": 0, "avg_response_time": 0},
            "secondary": {"requests": 0, "failures": 0, "avg_response_time": 0}
        }
        
        # Validate API keys
        if not self.api_keys["primary"]:
            raise ValueError("NVIDIA_API_KEY_1 (primary) not found in environment variables")
        
        if not self.api_keys["secondary"]:
            print("⚠️  NVIDIA_API_KEY_2 (secondary) not found - using single key mode")
            self.api_keys["secondary"] = self.api_keys["primary"]
    
    def select_api_key(self, agent_role: str) -> str:
        """
        Intelligent API key selection based on role and performance
        """
        
        assignment = self.key_assignments.get(agent_role, "auto")
        
        if assignment == "primary":
            return "primary"
        elif assignment == "secondary":
            return "secondary"
        elif assignment == "auto":
            # Intelligent auto-selection based on performance and load
            return self._smart_key_selection()
        else:
            return "primary"  # Fallback
    
    def _smart_key_selection(self) -> str:
        """
        Smart key selection based on performance metrics and load balancing
        """
        
        primary_load = self.key_performance["primary"]["requests"]
        secondary_load = self.key_performance["secondary"]["requests"]
        
        primary_failure_rate = (
            self.key_performance["primary"]["failures"] / 
            max(1, self.key_performance["primary"]["requests"])
        )
        secondary_failure_rate = (
            self.key_performance["secondary"]["failures"] / 
            max(1, self.key_performance["secondary"]["requests"])
        )
        
        # Prefer key with better performance and lower load
        if primary_failure_rate < secondary_failure_rate:
            return "primary"
        elif secondary_failure_rate < primary_failure_rate:
            return "secondary"
        else:
            # Load balance if performance is similar
            return "primary" if primary_load <= secondary_load else "secondary"
    
    def call_model(
        self, 
        agent_role: str, 
        messages: List[Dict], 
        max_tokens: int = 1024, 
        temperature: float = 0.1,
        tools: Optional[List] = None,
        tool_choice: Optional[str] = None
    ) -> Dict:
        """
        Enhanced model calling with dual-key support and failover
        """
        
        model = self.model_map.get(agent_role, self.model_map["fallback"])
        selected_key = self.select_api_key(agent_role)
        api_key = self.api_keys[selected_key]
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Add function calling parameters if provided
        if tools:
            payload["tools"] = tools
        if tool_choice:
            payload["tool_choice"] = tool_choice
        
        # Track performance
        start_time = time.time()
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=90  # Increased timeout for large models
            )
            response.raise_for_status()
            
            # Update performance metrics
            response_time = time.time() - start_time
            self._update_performance_metrics(selected_key, response_time, success=True)
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            # Update failure metrics
            self._update_performance_metrics(selected_key, 0, success=False)
            
            # Intelligent failover to other key
            if selected_key == "primary" and self.api_keys["secondary"] != self.api_keys["primary"]:
                return self._failover_request("secondary", headers, payload, agent_role)
            elif selected_key == "secondary" and self.api_keys["primary"] != self.api_keys["secondary"]:
                return self._failover_request("primary", headers, payload, agent_role)
            else:
                raise Exception(f"NIM API call failed for {agent_role} (model: {model}): {str(e)}")
    
    def _failover_request(self, fallback_key: str, headers: Dict, payload: Dict, agent_role: str) -> Dict:
        """
        Execute failover request with alternative API key
        """
        
        fallback_api_key = self.api_keys[fallback_key]
        headers["Authorization"] = f"Bearer {fallback_api_key}"
        
        start_time = time.time()
        
        try:
            print(f"🔄 Failover: Using {fallback_key} key for {agent_role}")
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=90
            )
            response.raise_for_status()
            
            # Update performance metrics for successful failover
            response_time = time.time() - start_time
            self._update_performance_metrics(fallback_key, response_time, success=True)
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self._update_performance_metrics(fallback_key, 0, success=False)
            raise Exception(f"Failover also failed for {agent_role}: {str(e)}")
    
    def _update_performance_metrics(self, key: str, response_time: float, success: bool):
        """
        Update performance tracking for intelligent routing
        """
        
        metrics = self.key_performance[key]
        metrics["requests"] += 1
        
        if success:
            # Update average response time
            current_avg = metrics["avg_response_time"]
            request_count = metrics["requests"]
            metrics["avg_response_time"] = (
                (current_avg * (request_count - 1) + response_time) / request_count
            )
        else:
            metrics["failures"] += 1
    
    def call_agent_simple(
        self, 
        agent_role: str, 
        prompt: str, 
        system_message: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Simplified agent calling with dual-key support
        """
        
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        response = self.call_model(agent_role, messages, **kwargs)
        return response["choices"][0]["message"]["content"]
    
    def get_performance_stats(self) -> Dict:
        """
        Get performance statistics for monitoring
        """
        
        return {
            "key_performance": self.key_performance,
            "key_assignments": self.key_assignments,
            "active_keys": {
                "primary": "active" if self.api_keys["primary"] else "missing",
                "secondary": "active" if self.api_keys["secondary"] and 
                            self.api_keys["secondary"] != self.api_keys["primary"] else "missing/duplicate"
            }
        }

# Global enhanced client instance
enhanced_nim_client = EnhancedNIMClient()

# Backward compatible functions
def call_nim_agent(agent_role: str, prompt: str, system_message: Optional[str] = None, **kwargs) -> str:
    """Global function for easy agent calls with dual-key support"""
    return enhanced_nim_client.call_agent_simple(agent_role, prompt, system_message, **kwargs)

def call_nim_with_tools(agent_role: str, messages: List[Dict], tools: List, **kwargs) -> Dict:
    """Global function for tool-enabled agent calls with dual-key support"""
    return enhanced_nim_client.call_model(agent_role, messages, tools=tools, **kwargs)

def get_nim_performance_stats() -> Dict:
    """Get NIM client performance statistics"""
    return enhanced_nim_client.get_performance_stats()

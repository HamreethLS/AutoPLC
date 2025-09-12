"""
Enhanced NVIDIA NIM API client with intelligent routing, performance tracking, and error recovery
Supports multiple model tiers with optimized routing and comprehensive error handling
"""

import os
import requests
import json
import time
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import logging
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelTier(str, Enum):
    HEAVY = "heavy"      # 70B+ models for complex reasoning
    MEDIUM = "medium"    # 7B-20B models for general tasks  
    LIGHT = "light"      # Small models for simple tasks
    NANO = "nano"        # Ultra-light models for tool calling

class ApiKeyStatus(str, Enum):
    ACTIVE = "active"
    RATE_LIMITED = "rate_limited" 
    ERROR = "error"
    UNAVAILABLE = "unavailable"

class RequestPriority(str, Enum):
    HIGH = "high"        # Critical requests (validation, error recovery)
    NORMAL = "normal"    # Standard requests (planning, coding)
    LOW = "low"          # Background requests (analytics, caching)

@dataclass
class ModelConfig:
    name: str
    tier: ModelTier
    max_tokens: int
    recommended_temperature: float
    cost_factor: float
    supports_tools: bool = False
    context_window: int = 4096
    rpm_limit: int = 60  # Requests per minute
    description: str = ""

@dataclass
class ApiKeyMetrics:
    requests: int = 0
    failures: int = 0
    avg_response_time: float = 0.0
    last_error: Optional[str] = None
    status: ApiKeyStatus = ApiKeyStatus.ACTIVE
    rate_limit_reset: Optional[datetime] = None
    success_rate: float = 1.0
    last_used: Optional[datetime] = None
    request_history: List[float] = field(default_factory=list)

@dataclass
class RequestMetrics:
    timestamp: datetime
    model: str
    response_time: float
    success: bool
    tokens_used: int = 0
    error: Optional[str] = None

class EnhancedNIMClient:
    """Advanced NVIDIA NIM client with intelligent routing, performance tracking, and error recovery"""
    
    def __init__(self):
        # Load and validate API keys
        self.api_keys = {
            "primary": os.getenv("NVIDIA_API_KEY_1"),
            "secondary": os.getenv("NVIDIA_API_KEY_2")
        }
        
        self.base_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        
        # Model configurations with your specified models
        self.model_configs = {
            "planner": ModelConfig(
                name="openai/gpt-oss-120b",
                tier=ModelTier.HEAVY,
                max_tokens=1024,
                recommended_temperature=0.1,
                cost_factor=0.8,
                supports_tools=False,
                context_window=8192,
                rpm_limit=30,
                description="OpenAI GPT-OSS (120B) for strategic planning and analysis"
            ),
            "coder": ModelConfig(
                name="qwen/qwen3-coder-480b-a35b-instruct", 
                tier=ModelTier.HEAVY,
                max_tokens=1500,
                recommended_temperature=0.05,
                cost_factor=1.0,
                supports_tools=False,
                context_window=16384,
                rpm_limit=20,
                description="Qwen3 Coder (480B) for complex, specialized code generation"
            ),
            "validator": ModelConfig(
                name="nvidia/llama-3.1-nemotron-ultra-253b-v1",
                tier=ModelTier.HEAVY,
                max_tokens=800,
                recommended_temperature=0.1,
                cost_factor=0.9,
                supports_tools=True,
                context_window=12288,
                rpm_limit=40,
                description="NVIDIA Nemotron Ultra (253B) for high-accuracy validation and analysis"
            ),
            "knowledge": ModelConfig(
                name="nvidia/llama-3.1-nemotron-ultra-253b-v1",
                tier=ModelTier.HEAVY,
                max_tokens=600,
                recommended_temperature=0.1,
                cost_factor=0.9,
                supports_tools=True,
                context_window=12288,
                rpm_limit=40,
                description="NVIDIA Nemotron Ultra (253B) for knowledge synthesis"
            ),
            "retrieval": ModelConfig(
                name="nvidia/llama-3.1-nemotron-ultra-253b-v1",
                tier=ModelTier.HEAVY,
                max_tokens=800,
                recommended_temperature=0.2,
                cost_factor=0.9,
                supports_tools=True,
                context_window=12288,
                rpm_limit=40,
                description="NVIDIA Nemotron Ultra (253B) for external research synthesis"
            ),
            "fallback": ModelConfig(
                name="nvidia/llama-3.1-nemotron-nano-8b-v1",
                tier=ModelTier.NANO,
                max_tokens=600,
                recommended_temperature=0.15,
                cost_factor=0.2,
                supports_tools=True,
                context_window=4096,
                rpm_limit=100,
                description="NVIDIA Nemotron Nano (8B) for error recovery and simple tasks"
            )
        }
        
        # Performance tracking and metrics
        self.key_metrics = {
            "primary": ApiKeyMetrics(),
            "secondary": ApiKeyMetrics()
        }
        
        self.request_history: List[RequestMetrics] = []
        self.model_performance: Dict[str, List[float]] = defaultdict(list)
        
        # Routing configuration
        self.routing_strategy = "intelligent"  # Options: round_robin, performance_based, cost_optimized, intelligent
        self.max_retries = 3
        self.base_timeout = 30
        self.circuit_breaker_threshold = 0.5  # 50% failure rate triggers circuit breaker
        
        # Rate limiting
        self.rate_limiters: Dict[str, Dict[str, List[datetime]]] = {
            "primary": defaultdict(list),
            "secondary": defaultdict(list)
        }
        
        # Validate configuration
        self._validate_setup()
    
    def _validate_setup(self):
        """Validate the client setup and configuration"""
        if not self.api_keys["primary"]:
            raise ValueError("NVIDIA_API_KEY_1 (primary) is required")
        
        if not self.api_keys["secondary"]:
            logger.warning("⚠️ NVIDIA_API_KEY_2 (secondary) not found - using single key mode")
            self.api_keys["secondary"] = self.api_keys["primary"]
        
        # Test API key validity
        if not self._test_api_key("primary"):
            logger.error("❌ Primary API key appears to be invalid")
        
        logger.info(f"✅ NIM Client initialized with {len([k for k in self.api_keys.values() if k])} API key(s)")
        logger.info(f"📊 Configured {len(self.model_configs)} models across {len(set(cfg.tier for cfg in self.model_configs.values()))} tiers")
    
    def _test_api_key(self, key_name: str) -> bool:
        """Test if an API key is valid"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_keys[key_name]}",
                "Content-Type": "application/json"
            }
            
            # Simple test request
            test_payload = {
                "model": "nvidia/llama-3.1-nemotron-nano-8b-v1",
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 1
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=test_payload,
                timeout=10
            )
            
            return response.status_code != 401  # Not unauthorized
            
        except Exception as e:
            logger.warning(f"API key test failed for {key_name}: {str(e)}")
            return False
    
    def _select_optimal_key(self, model_tier: ModelTier, priority: RequestPriority = RequestPriority.NORMAL) -> str:
        """Intelligently select the optimal API key based on multiple factors"""
        
        primary_metrics = self.key_metrics["primary"]
        secondary_metrics = self.key_metrics["secondary"]
        
        # Check circuit breaker status
        if primary_metrics.success_rate < self.circuit_breaker_threshold:
            if secondary_metrics.success_rate >= self.circuit_breaker_threshold:
                return "secondary"
        
        if secondary_metrics.success_rate < self.circuit_breaker_threshold:
            if primary_metrics.success_rate >= self.circuit_breaker_threshold:
                return "primary"
        
        # Check rate limiting
        if self._is_rate_limited("primary", model_tier):
            if not self._is_rate_limited("secondary", model_tier):
                return "secondary"
        
        if self._is_rate_limited("secondary", model_tier):
            return "primary"
        
        # Intelligent routing based on strategy
        if self.routing_strategy == "round_robin":
            return "primary" if primary_metrics.requests <= secondary_metrics.requests else "secondary"
        
        elif self.routing_strategy == "performance_based":
            # Select based on success rate and response time
            primary_score = primary_metrics.success_rate / max(0.1, primary_metrics.avg_response_time)
            secondary_score = secondary_metrics.success_rate / max(0.1, secondary_metrics.avg_response_time)
            return "primary" if primary_score >= secondary_score else "secondary"
        
        elif self.routing_strategy == "cost_optimized":
            # Distribute heavy models to secondary, light models to primary
            if model_tier in [ModelTier.HEAVY, ModelTier.MEDIUM]:
                return "secondary"
            else:
                return "primary"
        
        elif self.routing_strategy == "intelligent":
            # Advanced intelligent routing considering multiple factors
            primary_load = len(self.rate_limiters["primary"])
            secondary_load = len(self.rate_limiters["secondary"])
            
            # Factor in priority
            if priority == RequestPriority.HIGH:
                # Use the key with better recent performance
                recent_primary = self._get_recent_success_rate("primary")
                recent_secondary = self._get_recent_success_rate("secondary")
                return "primary" if recent_primary >= recent_secondary else "secondary"
            
            # Balanced approach for normal and low priority
            primary_score = (
                primary_metrics.success_rate * 0.4 +
                (1 / max(1, primary_metrics.avg_response_time)) * 0.3 +
                (1 / max(1, primary_load)) * 0.3
            )
            
            secondary_score = (
                secondary_metrics.success_rate * 0.4 +
                (1 / max(1, secondary_metrics.avg_response_time)) * 0.3 +
                (1 / max(1, secondary_load)) * 0.3
            )
            
            return "primary" if primary_score >= secondary_score else "secondary"
        
        return "primary"  # Default fallback
    
    def _is_rate_limited(self, key_name: str, model_tier: ModelTier) -> bool:
        """Check if a key is rate limited for a specific model tier"""
        now = datetime.now()
        model_name = next(
            (cfg.name for cfg in self.model_configs.values() if cfg.tier == model_tier),
            "default"
        )
        
        # Clean old requests (older than 1 minute)
        self.rate_limiters[key_name][model_name] = [
            req_time for req_time in self.rate_limiters[key_name][model_name]
            if now - req_time < timedelta(minutes=1)
        ]
        
        # Check if we're at the limit
        rpm_limit = next(
            (cfg.rpm_limit for cfg in self.model_configs.values() if cfg.tier == model_tier),
            60
        )
        
        return len(self.rate_limiters[key_name][model_name]) >= rpm_limit
    
    def _get_recent_success_rate(self, key_name: str, window_minutes: int = 5) -> float:
        """Get recent success rate for a key within a time window"""
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        recent_requests = [
            req for req in self.request_history
            if req.timestamp >= cutoff
        ]
        
        if not recent_requests:
            return self.key_metrics[key_name].success_rate
        
        successes = sum(1 for req in recent_requests if req.success)
        return successes / len(recent_requests)
    
    async def call_agent_simple(
        self,
        agent_role: str,
        prompt: str,
        system_message: Optional[str] = None,
        priority: RequestPriority = RequestPriority.NORMAL,
        **kwargs
    ) -> str:
        """Simplified async agent calling with enhanced error handling and routing"""
        
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        response = await self.call_model_async(
            agent_role=agent_role,
            messages=messages,
            priority=priority,
            **kwargs
        )
        
        return response["choices"][0]["message"]["content"]
    
    async def call_model_async(
        self,
        agent_role: str,
        messages: List[Dict],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        tools: Optional[List] = None,
        tool_choice: Optional[str] = None,
        priority: RequestPriority = RequestPriority.NORMAL,
        **kwargs
    ) -> Dict:
        """Enhanced async model calling with intelligent routing and comprehensive error handling"""
        
        # Get model configuration
        config = self.model_configs.get(agent_role)
        if not config:
            logger.warning(f"Unknown agent role: {agent_role}, using fallback")
            config = self.model_configs["fallback"]
        
        # Use provided parameters or defaults from config
        final_max_tokens = max_tokens or config.max_tokens
        final_temperature = temperature if temperature is not None else config.recommended_temperature
        
        # Validate tool calling support
        if tools and not config.supports_tools:
            logger.warning(f"Model {config.name} doesn't support tools, removing tool parameters")
            tools = None
            tool_choice = None
        
        # Select API key intelligently
        selected_key = self._select_optimal_key(config.tier, priority)
        
        # Prepare request payload
        payload = {
            "model": config.name,
            "messages": messages,
            "temperature": final_temperature,
            "max_tokens": final_max_tokens,
            **kwargs  # Allow additional parameters
        }
        
        # Add function calling if provided and supported
        if tools:
            payload["tools"] = tools
        if tool_choice:
            payload["tool_choice"] = tool_choice
        
        # Execute request with intelligent retry logic
        return await self._execute_request_with_retry(
            selected_key, payload, agent_role, config, priority
        )
    
    async def _execute_request_with_retry(
        self, 
        api_key_name: str, 
        payload: Dict, 
        agent_role: str,
        config: ModelConfig,
        priority: RequestPriority
    ) -> Dict:
        """Execute request with intelligent retry logic and circuit breaking"""
        
        for attempt in range(self.max_retries):
            start_time = time.time()
            
            try:
                # Update rate limiting
                self._record_request_attempt(api_key_name, config.name)
                
                # Make the request
                response = await self._make_async_request(api_key_name, payload, config)
                
                # Record successful request
                response_time = time.time() - start_time
                self._update_metrics(api_key_name, response_time, success=True, config=config)
                
                # Record request metrics
                self._record_request_metrics(
                    model=config.name,
                    response_time=response_time,
                    success=True,
                    tokens_used=response.get("usage", {}).get("total_tokens", 0)
                )
                
                return response
                
            except requests.exceptions.HTTPError as e:
                response_time = time.time() - start_time
                
                if hasattr(e, 'response') and e.response.status_code == 429:  # Rate limited
                    self._handle_rate_limit(api_key_name)
                    
                    # Try other key if available and not the last attempt
                    if attempt < self.max_retries - 1:
                        other_key = "secondary" if api_key_name == "primary" else "primary"
                        if other_key != api_key_name and self.api_keys[other_key] != self.api_keys[api_key_name]:
                            logger.info(f"🔄 Rate limited, switching to {other_key} key")
                            api_key_name = other_key
                            continue
                
                # Update failure metrics
                error_msg = str(e)
                self._update_metrics(api_key_name, response_time, success=False, error=error_msg, config=config)
                self._record_request_metrics(
                    model=config.name,
                    response_time=response_time,
                    success=False,
                    error=error_msg
                )
                
                # If this is the last attempt, raise the exception
                if attempt == self.max_retries - 1:
                    raise Exception(f"NIM API failed for {agent_role} after {self.max_retries} attempts: {error_msg}")
                
                # Exponential backoff with jitter
                backoff_time = (2 ** attempt) + (time.time() % 1)  # Add jitter
                logger.info(f"🔄 Retrying {agent_role} request in {backoff_time:.1f}s (attempt {attempt + 1}/{self.max_retries})")
                await asyncio.sleep(backoff_time)
            
            except Exception as e:
                response_time = time.time() - start_time
                error_msg = str(e)
                
                self._update_metrics(api_key_name, response_time, success=False, error=error_msg, config=config)
                self._record_request_metrics(
                    model=config.name,
                    response_time=response_time,
                    success=False,
                    error=error_msg
                )
                
                if attempt == self.max_retries - 1:
                    raise Exception(f"NIM API error for {agent_role}: {error_msg}")
                
                backoff_time = (2 ** attempt) + (time.time() % 1)
                await asyncio.sleep(backoff_time)
        
        # Should never reach here due to exception handling above
        raise Exception(f"Unexpected failure in request execution for {agent_role}")
    
    async def _make_async_request(self, api_key_name: str, payload: Dict, config: ModelConfig) -> Dict:
        """Make async HTTP request with timeout and proper error handling"""
        
        api_key = self.api_keys[api_key_name]
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Calculate timeout based on expected response size
        timeout = min(self.base_timeout * (payload.get("max_tokens", 500) / 500), 120)
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as session:
            async with session.post(
                self.base_url,
                headers=headers,
                json=payload
            ) as response:
                response.raise_for_status()
                return await response.json()
    
    def _record_request_attempt(self, key_name: str, model_name: str):
        """Record a request attempt for rate limiting"""
        now = datetime.now()
        self.rate_limiters[key_name][model_name].append(now)
    
    def _handle_rate_limit(self, key_name: str):
        """Handle rate limiting for a specific key"""
        self.key_metrics[key_name].status = ApiKeyStatus.RATE_LIMITED
        self.key_metrics[key_name].rate_limit_reset = datetime.now() + timedelta(minutes=1)
        logger.warning(f"🚫 API key {key_name} is rate limited")
    
    def _update_metrics(
        self, 
        key_name: str, 
        response_time: float, 
        success: bool, 
        config: ModelConfig,
        error: Optional[str] = None
    ):
        """Update comprehensive performance metrics for a key"""
        
        metrics = self.key_metrics[key_name]
        metrics.requests += 1
        metrics.last_used = datetime.now()
        
        # Update response time (exponential moving average)
        if metrics.avg_response_time == 0:
            metrics.avg_response_time = response_time
        else:
            # Use exponential moving average with alpha = 0.1
            metrics.avg_response_time = 0.9 * metrics.avg_response_time + 0.1 * response_time
        
        if success:
            metrics.status = ApiKeyStatus.ACTIVE
            # Update success rate (exponential moving average)
            metrics.success_rate = 0.95 * metrics.success_rate + 0.05 * 1.0
        else:
            metrics.failures += 1
            metrics.last_error = error
            metrics.success_rate = 0.95 * metrics.success_rate + 0.05 * 0.0
            
            # Check if we should trigger circuit breaker
            if metrics.success_rate < self.circuit_breaker_threshold:
                metrics.status = ApiKeyStatus.ERROR
                logger.error(f"🔴 Circuit breaker triggered for {key_name} key (success rate: {metrics.success_rate:.2f})")
        
        # Keep recent request history for trend analysis
        metrics.request_history.append(response_time)
        if len(metrics.request_history) > 100:  # Keep last 100 requests
            metrics.request_history.pop(0)
    
    def _record_request_metrics(
        self, 
        model: str, 
        response_time: float, 
        success: bool,
        tokens_used: int = 0,
        error: Optional[str] = None
    ):
        """Record detailed request metrics for analytics"""
        
        metrics = RequestMetrics(
            timestamp=datetime.now(),
            model=model,
            response_time=response_time,
            success=success,
            tokens_used=tokens_used,
            error=error
        )
        
        self.request_history.append(metrics)
        
        # Keep only recent history (last 1000 requests)
        if len(self.request_history) > 1000:
            self.request_history.pop(0)
        
        # Update model-specific performance tracking
        self.model_performance[model].append(response_time)
        if len(self.model_performance[model]) > 50:  # Keep last 50 requests per model
            self.model_performance[model].pop(0)
    
    # Tool calling support methods
    async def call_with_tools(
        self,
        agent_role: str,
        messages: List[Dict],
        tools: List[Dict],
        tool_choice: Optional[str] = "auto",
        **kwargs
    ) -> Dict:
        """Enhanced tool calling with automatic model selection"""
        
        # Ensure the selected model supports tools
        config = self.model_configs.get(agent_role, self.model_configs["fallback"])
        
        if not config.supports_tools:
            # Find a model that supports tools
            tool_capable_roles = [
                role for role, cfg in self.model_configs.items() 
                if cfg.supports_tools
            ]
            
            if tool_capable_roles:
                fallback_role = tool_capable_roles[0]  # Use first available tool-capable model
                logger.info(f"🔧 Switching from {agent_role} to {fallback_role} for tool calling")
                agent_role = fallback_role
            else:
                raise ValueError("No models available that support tool calling")
        
        return await self.call_model_async(
            agent_role=agent_role,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            **kwargs
        )
    
    # Synchronous compatibility methods
    def call_agent_simple_sync(
        self, 
        agent_role: str, 
        prompt: str, 
        system_message: Optional[str] = None,
        **kwargs
    ) -> str:
        """Synchronous wrapper for backward compatibility"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.call_agent_simple(agent_role, prompt, system_message, **kwargs)
        )
    
    def call_model_sync(self, agent_role: str, messages: List[Dict], **kwargs) -> Dict:
        """Synchronous model calling for backward compatibility"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.call_model_async(agent_role, messages, **kwargs)
        )
    
    # Analytics and monitoring methods
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics and analytics"""
        
        current_time = datetime.now()
        
        # Calculate overall metrics
        total_requests = sum(metrics.requests for metrics in self.key_metrics.values())
        total_failures = sum(metrics.failures for metrics in self.key_metrics.values())
        overall_success_rate = 1 - (total_failures / max(1, total_requests))
        
        # Model performance analysis
        model_stats = {}
        for model, response_times in self.model_performance.items():
            if response_times:
                model_stats[model] = {
                    "avg_response_time": sum(response_times) / len(response_times),
                    "min_response_time": min(response_times),
                    "max_response_time": max(response_times),
                    "total_requests": len(response_times)
                }
        
        # Recent performance (last hour)
        recent_cutoff = current_time - timedelta(hours=1)
        recent_requests = [req for req in self.request_history if req.timestamp >= recent_cutoff]
        recent_success_rate = (
            sum(1 for req in recent_requests if req.success) / max(1, len(recent_requests))
        )
        
        return {
            "overall": {
                "total_requests": total_requests,
                "total_failures": total_failures,
                "success_rate": overall_success_rate,
                "recent_success_rate": recent_success_rate
            },
            "api_keys": {
                name: {
                    "requests": metrics.requests,
                    "failures": metrics.failures,
                    "success_rate": metrics.success_rate,
                    "avg_response_time": metrics.avg_response_time,
                    "status": metrics.status.value,
                    "last_used": metrics.last_used.isoformat() if metrics.last_used else None,
                    "last_error": metrics.last_error
                }
                for name, metrics in self.key_metrics.items()
            },
            "models": {
                role: {
                    "model_name": config.name,
                    "tier": config.tier.value,
                    "supports_tools": config.supports_tools,
                    "max_tokens": config.max_tokens,
                    "performance": model_stats.get(config.name, {})
                }
                for role, config in self.model_configs.items()
            },
            "routing": {
                "strategy": self.routing_strategy,
                "circuit_breaker_threshold": self.circuit_breaker_threshold,
                "max_retries": self.max_retries
            },
            "recent_requests": len(recent_requests),
            "timestamp": current_time.isoformat()
        }
    
    def optimize_routing_strategy(self):
        """Automatically optimize routing strategy based on performance data"""
        
        if len(self.request_history) < 50:  # Not enough data
            return
        
        primary_performance = self.key_metrics["primary"].success_rate * (1 / max(0.1, self.key_metrics["primary"].avg_response_time))
        secondary_performance = self.key_metrics["secondary"].success_rate * (1 / max(0.1, self.key_metrics["secondary"].avg_response_time))
        
        performance_diff = abs(primary_performance - secondary_performance) / max(primary_performance, secondary_performance)
        
        if performance_diff < 0.1:  # Similar performance
            self.routing_strategy = "round_robin"
            logger.info("🔄 Optimized routing strategy: round_robin (similar performance)")
        else:
            self.routing_strategy = "intelligent"
            logger.info("🧠 Optimized routing strategy: intelligent (performance difference detected)")
    
    def reset_circuit_breakers(self):
        """Reset circuit breakers for all API keys"""
        for metrics in self.key_metrics.values():
            if metrics.status == ApiKeyStatus.ERROR:
                metrics.status = ApiKeyStatus.ACTIVE
                metrics.success_rate = 0.5  # Reset to neutral
                logger.info("🔄 Circuit breaker reset")
    
    def get_model_recommendations(self) -> Dict[str, str]:
        """Get model recommendations based on performance data"""
        
        recommendations = {}
        
        for role, config in self.model_configs.items():
            model_perf = self.model_performance.get(config.name, [])
            
            if not model_perf:
                recommendations[role] = "No performance data available"
                continue
            
            avg_response = sum(model_perf) / len(model_perf)
            
            if avg_response < 1.0:
                recommendations[role] = "✅ Excellent performance"
            elif avg_response < 3.0:
                recommendations[role] = "✅ Good performance"
            elif avg_response < 5.0:
                recommendations[role] = "⚠️ Acceptable performance"
            else:
                recommendations[role] = "❌ Consider model optimization"
        
        return recommendations
    
    def export_metrics(self) -> Dict[str, Any]:
        """Export detailed metrics for external analysis"""
        return {
            "key_metrics": {
                name: {
                    "requests": metrics.requests,
                    "failures": metrics.failures,
                    "success_rate": metrics.success_rate,
                    "avg_response_time": metrics.avg_response_time,
                    "request_history": metrics.request_history[-50:]  # Last 50 requests
                }
                for name, metrics in self.key_metrics.items()
            },
            "request_history": [
                {
                    "timestamp": req.timestamp.isoformat(),
                    "model": req.model,
                    "response_time": req.response_time,
                    "success": req.success,
                    "tokens_used": req.tokens_used,
                    "error": req.error
                }
                for req in self.request_history[-100:]  # Last 100 requests
            ],
            "model_configs": {
                role: {
                    "name": config.name,
                    "tier": config.tier.value,
                    "description": config.description,
                    "supports_tools": config.supports_tools,
                    "cost_factor": config.cost_factor
                }
                for role, config in self.model_configs.items()
            }
        }

# Global enhanced client instance
enhanced_nim_client = EnhancedNIMClient()

# Backward compatible functions for existing code
def call_nim_agent(agent_role: str, prompt: str, system_message: Optional[str] = None, **kwargs) -> str:
    """Legacy synchronous function for backward compatibility"""
    return enhanced_nim_client.call_agent_simple_sync(agent_role, prompt, system_message, **kwargs)

async def call_nim_agent_async(agent_role: str, prompt: str, system_message: Optional[str] = None, **kwargs) -> str:
    """Async version of the legacy function"""
    return await enhanced_nim_client.call_agent_simple(agent_role, prompt, system_message, **kwargs)

def call_nim_with_tools(agent_role: str, messages: List[Dict], tools: List, **kwargs) -> Dict:
    """Legacy function for tool-enabled calls"""
    return enhanced_nim_client.call_model_sync(agent_role, messages, tools=tools, **kwargs)

async def call_nim_with_tools_async(agent_role: str, messages: List[Dict], tools: List, **kwargs) -> Dict:
    """Async version of tool-enabled calls"""
    return await enhanced_nim_client.call_model_async(agent_role, messages, tools=tools, **kwargs)

def get_nim_performance_stats() -> Dict:
    """Get NIM client performance statistics"""
    return enhanced_nim_client.get_performance_stats()

def optimize_nim_routing():
    """Optimize NIM client routing strategy"""
    enhanced_nim_client.optimize_routing_strategy()

# Utility functions for monitoring and debugging
def log_nim_status():
    """Log current NIM client status"""
    stats = enhanced_nim_client.get_performance_stats()
    logger.info(f"🔍 NIM Status: {stats['overall']['success_rate']:.2f} success rate, {stats['overall']['total_requests']} total requests")

def get_model_info(agent_role: str) -> Dict[str, Any]:
    """Get information about a specific model configuration"""
    config = enhanced_nim_client.model_configs.get(agent_role)
    if not config:
        return {"error": f"Unknown agent role: {agent_role}"}
    
    return {
        "name": config.name,
        "tier": config.tier.value,
        "max_tokens": config.max_tokens,
        "supports_tools": config.supports_tools,
        "description": config.description,
        "cost_factor": config.cost_factor
    }

# Export the client instance and key functions
__all__ = [
    'enhanced_nim_client',
    'call_nim_agent',
    'call_nim_agent_async', 
    'call_nim_with_tools',
    'call_nim_with_tools_async',
    'get_nim_performance_stats',
    'optimize_nim_routing',
    'log_nim_status',
    'get_model_info',
    'ModelTier',
    'RequestPriority',
    'EnhancedNIMClient'
]

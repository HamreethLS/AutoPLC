"""Monitor agent for runtime telemetry and system health monitoring."""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from agents.base_agent import LLMAgent
from models.schemas import AgentRole, AgentTask, TelemetryData


@dataclass
class AlertRule:
    """Configuration for monitoring alert rules."""
    name: str
    metric: str
    threshold: float
    operator: str  # gt, lt, eq, gte, lte
    severity: str  # info, warning, error, critical
    description: str


class MonitorAgent(LLMAgent):
    """Agent responsible for monitoring runtime telemetry and system health."""
    
    def __init__(self, llm=None):
        super().__init__(
            role=AgentRole.MONITOR,
            name="PLC Runtime Monitor",
            description="Monitors PLC runtime telemetry and detects anomalies",
            llm=llm
        )
        
        # Monitoring configuration
        self.monitoring_enabled = True
        self.collection_interval = 5  # seconds
        self.retention_period = 7  # days
        
        # Alert rules for different metrics
        self.alert_rules = [
            AlertRule(
                name="high_cycle_time",
                metric="cycle_time_ms",
                threshold=100.0,
                operator="gt",
                severity="warning",
                description="PLC cycle time exceeds 100ms"
            ),
            AlertRule(
                name="critical_cycle_time",
                metric="cycle_time_ms",
                threshold=200.0,
                operator="gt",
                severity="critical",
                description="PLC cycle time exceeds 200ms - system may be overloaded"
            ),
            AlertRule(
                name="memory_usage_high",
                metric="memory_usage_percent",
                threshold=80.0,
                operator="gt",
                severity="warning",
                description="Memory usage exceeds 80%"
            ),
            AlertRule(
                name="error_rate_high",
                metric="error_rate",
                threshold=0.05,
                operator="gt",
                severity="error",
                description="Error rate exceeds 5%"
            ),
            AlertRule(
                name="communication_timeout",
                metric="communication_timeout_count",
                threshold=0,
                operator="gt",
                severity="error",
                description="Communication timeouts detected"
            ),
            AlertRule(
                name="safety_system_fault",
                metric="safety_fault_count",
                threshold=0,
                operator="gt",
                severity="critical",
                description="Safety system fault detected"
            )
        ]
        
        # Telemetry data buffer
        self.telemetry_buffer = []
        self.max_buffer_size = 1000
        
        # Anomaly detection parameters
        self.baseline_window = 100  # samples for baseline
        self.anomaly_threshold = 2.0  # standard deviations
        
        # System health metrics
        self.health_metrics = {
            "overall_health": 100,
            "last_update": datetime.utcnow(),
            "active_alerts": [],
            "system_uptime": 0,
            "total_cycles": 0,
            "error_count": 0
        }
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the monitor agent."""
        return """
You are a PLC Runtime Monitor Agent specialized in real-time telemetry monitoring and anomaly detection.

Your responsibilities:
1. Collect and analyze runtime telemetry data from PLC systems
2. Detect anomalies and performance degradation
3. Generate alerts for critical conditions
4. Monitor system health and availability
5. Track performance trends and patterns
6. Provide diagnostic information for troubleshooting

Monitoring capabilities:
- Real-time cycle time monitoring
- Memory and CPU usage tracking
- Communication status monitoring
- Safety system health checks
- Error rate and fault detection
- Performance trend analysis

Alert severity levels:
- INFO: Informational messages
- WARNING: Potential issues requiring attention
- ERROR: Errors that may affect operation
- CRITICAL: Critical failures requiring immediate action

Always prioritize safety-critical alerts and provide actionable diagnostic information.
"""
    
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        """Process a monitoring task."""
        task_type = task.task_type
        input_data = task.input_data
        
        if task_type == "start_monitoring":
            return await self._start_monitoring(input_data)
        elif task_type == "collect_telemetry":
            return await self._collect_telemetry(input_data)
        elif task_type == "analyze_metrics":
            return await self._analyze_metrics(input_data)
        elif task_type == "detect_anomalies":
            return await self._detect_anomalies(input_data)
        elif task_type == "generate_health_report":
            return await self._generate_health_report(input_data)
        elif task_type == "check_alerts":
            return await self._check_alerts(input_data)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _start_monitoring(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Start monitoring a PLC system."""
        system_id = input_data.get("system_id", "default")
        monitoring_config = input_data.get("config", {})
        
        # Update configuration
        self.collection_interval = monitoring_config.get("collection_interval", self.collection_interval)
        self.monitoring_enabled = True
        
        # Initialize monitoring session
        monitoring_session = {
            "system_id": system_id,
            "started_at": datetime.utcnow(),
            "config": monitoring_config,
            "status": "active"
        }
        
        # Start background monitoring task
        asyncio.create_task(self._monitoring_loop(system_id))
        
        return {
            "monitoring_session": monitoring_session,
            "collection_interval": self.collection_interval,
            "alert_rules_count": len(self.alert_rules),
            "status": "monitoring_started"
        }
    
    async def _collect_telemetry(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Collect telemetry data from a PLC system."""
        system_id = input_data.get("system_id", "default")
        
        # Simulate telemetry data collection
        # In a real implementation, this would connect to actual PLC systems
        telemetry_data = await self._simulate_telemetry_collection(system_id)
        
        # Add to buffer
        self.telemetry_buffer.append(telemetry_data)
        
        # Maintain buffer size
        if len(self.telemetry_buffer) > self.max_buffer_size:
            self.telemetry_buffer.pop(0)
        
        # Check for alerts
        alerts = self._evaluate_alert_rules(telemetry_data)
        
        return {
            "telemetry_data": telemetry_data,
            "alerts": alerts,
            "buffer_size": len(self.telemetry_buffer),
            "collection_timestamp": datetime.utcnow().isoformat()
        }
    
    async def _analyze_metrics(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze collected metrics for trends and patterns."""
        time_window = input_data.get("time_window", 3600)  # 1 hour default
        
        if not self.telemetry_buffer:
            return {"analysis": "No telemetry data available"}
        
        # Filter data by time window
        cutoff_time = datetime.utcnow() - timedelta(seconds=time_window)
        recent_data = [
            data for data in self.telemetry_buffer 
            if datetime.fromisoformat(data["timestamp"]) >= cutoff_time
        ]
        
        if not recent_data:
            return {"analysis": "No recent telemetry data available"}
        
        # Calculate metrics
        analysis = {
            "time_window": time_window,
            "sample_count": len(recent_data),
            "metrics": {}
        }
        
        # Analyze cycle times
        cycle_times = [data["metrics"].get("cycle_time_ms", 0) for data in recent_data]
        if cycle_times:
            analysis["metrics"]["cycle_time"] = {
                "avg": sum(cycle_times) / len(cycle_times),
                "min": min(cycle_times),
                "max": max(cycle_times),
                "trend": self._calculate_trend(cycle_times)
            }
        
        # Analyze memory usage
        memory_usage = [data["metrics"].get("memory_usage_percent", 0) for data in recent_data]
        if memory_usage:
            analysis["metrics"]["memory_usage"] = {
                "avg": sum(memory_usage) / len(memory_usage),
                "min": min(memory_usage),
                "max": max(memory_usage),
                "trend": self._calculate_trend(memory_usage)
            }
        
        # Analyze error rates
        error_counts = [data["metrics"].get("error_count", 0) for data in recent_data]
        total_cycles = sum(data["metrics"].get("cycle_count", 1) for data in recent_data)
        error_rate = sum(error_counts) / total_cycles if total_cycles > 0 else 0
        
        analysis["metrics"]["error_rate"] = {
            "current": error_rate,
            "total_errors": sum(error_counts),
            "total_cycles": total_cycles
        }
        
        # Generate insights
        analysis["insights"] = self._generate_insights(analysis["metrics"])
        
        return analysis
    
    async def _detect_anomalies(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect anomalies in telemetry data."""
        if len(self.telemetry_buffer) < self.baseline_window:
            return {
                "anomalies": [],
                "status": "insufficient_data",
                "message": f"Need at least {self.baseline_window} samples for anomaly detection"
            }
        
        # Get recent data for analysis
        recent_data = self.telemetry_buffer[-50:]  # Last 50 samples
        baseline_data = self.telemetry_buffer[-self.baseline_window:-50]  # Baseline window
        
        anomalies = []
        
        # Check cycle time anomalies
        cycle_time_anomalies = self._detect_metric_anomalies(
            recent_data, baseline_data, "cycle_time_ms", "Cycle Time"
        )
        anomalies.extend(cycle_time_anomalies)
        
        # Check memory usage anomalies
        memory_anomalies = self._detect_metric_anomalies(
            recent_data, baseline_data, "memory_usage_percent", "Memory Usage"
        )
        anomalies.extend(memory_anomalies)
        
        # Check for pattern anomalies
        pattern_anomalies = self._detect_pattern_anomalies(recent_data)
        anomalies.extend(pattern_anomalies)
        
        return {
            "anomalies": anomalies,
            "detection_timestamp": datetime.utcnow().isoformat(),
            "baseline_samples": len(baseline_data),
            "analysis_samples": len(recent_data)
        }
    
    async def _generate_health_report(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a comprehensive system health report."""
        report_period = input_data.get("period", 3600)  # 1 hour default
        
        # Update health metrics
        self._update_health_metrics()
        
        # Analyze recent telemetry
        analysis_result = await self._analyze_metrics({"time_window": report_period})
        
        # Detect anomalies
        anomaly_result = await self._detect_anomalies({})
        
        # Generate health score
        health_score = self._calculate_health_score(analysis_result, anomaly_result)
        
        health_report = {
            "report_timestamp": datetime.utcnow().isoformat(),
            "report_period": report_period,
            "overall_health_score": health_score,
            "system_status": self._determine_system_status(health_score),
            "health_metrics": self.health_metrics,
            "performance_analysis": analysis_result,
            "anomalies": anomaly_result.get("anomalies", []),
            "active_alerts": self.health_metrics["active_alerts"],
            "recommendations": self._generate_health_recommendations(health_score, analysis_result)
        }
        
        return health_report
    
    async def _check_alerts(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check and manage system alerts."""
        if not self.telemetry_buffer:
            return {"alerts": [], "status": "no_data"}
        
        latest_data = self.telemetry_buffer[-1]
        current_alerts = self._evaluate_alert_rules(latest_data)
        
        # Update active alerts
        self.health_metrics["active_alerts"] = current_alerts
        
        # Categorize alerts by severity
        alert_summary = {
            "critical": [a for a in current_alerts if a["severity"] == "critical"],
            "error": [a for a in current_alerts if a["severity"] == "error"],
            "warning": [a for a in current_alerts if a["severity"] == "warning"],
            "info": [a for a in current_alerts if a["severity"] == "info"]
        }
        
        return {
            "alerts": current_alerts,
            "alert_summary": alert_summary,
            "total_alerts": len(current_alerts),
            "highest_severity": self._get_highest_severity(current_alerts),
            "check_timestamp": datetime.utcnow().isoformat()
        }
    
    async def _monitoring_loop(self, system_id: str):
        """Background monitoring loop."""
        while self.monitoring_enabled:
            try:
                # Collect telemetry
                await self._collect_telemetry({"system_id": system_id})
                
                # Check for critical alerts
                if self.telemetry_buffer:
                    latest_data = self.telemetry_buffer[-1]
                    alerts = self._evaluate_alert_rules(latest_data)
                    critical_alerts = [a for a in alerts if a["severity"] == "critical"]
                    
                    if critical_alerts:
                        self.logger.critical(f"Critical alerts detected: {critical_alerts}")
                
                # Wait for next collection interval
                await asyncio.sleep(self.collection_interval)
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {str(e)}")
                await asyncio.sleep(self.collection_interval)
    
    async def _simulate_telemetry_collection(self, system_id: str) -> Dict[str, Any]:
        """Simulate telemetry data collection from PLC system."""
        import random
        
        # Simulate realistic PLC telemetry data
        base_cycle_time = 50  # 50ms base cycle time
        cycle_time_variation = random.uniform(-10, 20)  # Some variation
        
        telemetry = {
            "system_id": system_id,
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                "cycle_time_ms": max(1, base_cycle_time + cycle_time_variation),
                "memory_usage_percent": random.uniform(30, 85),
                "cpu_usage_percent": random.uniform(20, 70),
                "cycle_count": random.randint(1000, 2000),
                "error_count": random.randint(0, 5),
                "communication_timeout_count": random.randint(0, 2),
                "safety_fault_count": random.randint(0, 1) if random.random() < 0.05 else 0,
                "io_update_time_ms": random.uniform(1, 5),
                "network_latency_ms": random.uniform(1, 10)
            },
            "tags": {
                "system_type": "plc",
                "location": "factory_floor",
                "criticality": "high"
            }
        }
        
        # Add some realistic patterns
        current_hour = datetime.utcnow().hour
        if 8 <= current_hour <= 17:  # Business hours - higher load
            telemetry["metrics"]["cycle_time_ms"] *= 1.2
            telemetry["metrics"]["cpu_usage_percent"] *= 1.3
        
        return telemetry
    
    def _evaluate_alert_rules(self, telemetry_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate alert rules against telemetry data."""
        alerts = []
        metrics = telemetry_data.get("metrics", {})
        
        for rule in self.alert_rules:
            metric_value = metrics.get(rule.metric, 0)
            
            # Evaluate rule condition
            triggered = False
            if rule.operator == "gt" and metric_value > rule.threshold:
                triggered = True
            elif rule.operator == "lt" and metric_value < rule.threshold:
                triggered = True
            elif rule.operator == "gte" and metric_value >= rule.threshold:
                triggered = True
            elif rule.operator == "lte" and metric_value <= rule.threshold:
                triggered = True
            elif rule.operator == "eq" and metric_value == rule.threshold:
                triggered = True
            
            if triggered:
                alerts.append({
                    "rule_name": rule.name,
                    "severity": rule.severity,
                    "description": rule.description,
                    "metric": rule.metric,
                    "current_value": metric_value,
                    "threshold": rule.threshold,
                    "timestamp": telemetry_data["timestamp"]
                })
        
        return alerts
    
    def _detect_metric_anomalies(self, recent_data: List[Dict], baseline_data: List[Dict], 
                                metric_name: str, metric_display_name: str) -> List[Dict[str, Any]]:
        """Detect anomalies in a specific metric."""
        anomalies = []
        
        # Extract metric values
        recent_values = [data["metrics"].get(metric_name, 0) for data in recent_data]
        baseline_values = [data["metrics"].get(metric_name, 0) for data in baseline_data]
        
        if not baseline_values or not recent_values:
            return anomalies
        
        # Calculate baseline statistics
        baseline_mean = sum(baseline_values) / len(baseline_values)
        baseline_variance = sum((x - baseline_mean) ** 2 for x in baseline_values) / len(baseline_values)
        baseline_std = baseline_variance ** 0.5
        
        # Check for anomalies in recent data
        for i, value in enumerate(recent_values):
            if baseline_std > 0:
                z_score = abs(value - baseline_mean) / baseline_std
                
                if z_score > self.anomaly_threshold:
                    anomalies.append({
                        "type": "statistical_anomaly",
                        "metric": metric_name,
                        "metric_display_name": metric_display_name,
                        "current_value": value,
                        "baseline_mean": baseline_mean,
                        "z_score": z_score,
                        "severity": "warning" if z_score < 3.0 else "error",
                        "description": f"{metric_display_name} value {value} deviates significantly from baseline (z-score: {z_score:.2f})"
                    })
        
        return anomalies
    
    def _detect_pattern_anomalies(self, recent_data: List[Dict]) -> List[Dict[str, Any]]:
        """Detect pattern-based anomalies."""
        anomalies = []
        
        if len(recent_data) < 10:
            return anomalies
        
        # Check for sudden spikes in cycle time
        cycle_times = [data["metrics"].get("cycle_time_ms", 0) for data in recent_data]
        
        for i in range(1, len(cycle_times)):
            if cycle_times[i] > cycle_times[i-1] * 2 and cycle_times[i] > 100:
                anomalies.append({
                    "type": "sudden_spike",
                    "metric": "cycle_time_ms",
                    "description": f"Sudden spike in cycle time: {cycle_times[i]:.1f}ms",
                    "severity": "warning",
                    "current_value": cycle_times[i],
                    "previous_value": cycle_times[i-1]
                })
        
        return anomalies
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction for a series of values."""
        if len(values) < 2:
            return "stable"
        
        # Simple linear trend calculation
        n = len(values)
        sum_x = sum(range(n))
        sum_y = sum(values)
        sum_xy = sum(i * values[i] for i in range(n))
        sum_x2 = sum(i * i for i in range(n))
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        if slope > 0.1:
            return "increasing"
        elif slope < -0.1:
            return "decreasing"
        else:
            return "stable"
    
    def _generate_insights(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate insights from metrics analysis."""
        insights = []
        
        # Cycle time insights
        if "cycle_time" in metrics:
            cycle_time = metrics["cycle_time"]
            if cycle_time["avg"] > 100:
                insights.append("Average cycle time is high - consider optimization")
            if cycle_time["trend"] == "increasing":
                insights.append("Cycle time is trending upward - monitor for performance degradation")
        
        # Memory usage insights
        if "memory_usage" in metrics:
            memory = metrics["memory_usage"]
            if memory["avg"] > 80:
                insights.append("High memory usage detected - check for memory leaks")
            if memory["max"] > 95:
                insights.append("Memory usage peaked above 95% - system may be under stress")
        
        # Error rate insights
        if "error_rate" in metrics:
            error_rate = metrics["error_rate"]["current"]
            if error_rate > 0.01:
                insights.append(f"Error rate is {error_rate*100:.1f}% - investigate error causes")
        
        return insights
    
    def _update_health_metrics(self):
        """Update system health metrics."""
        if self.telemetry_buffer:
            latest_data = self.telemetry_buffer[-1]
            
            # Update cycle count
            self.health_metrics["total_cycles"] += latest_data["metrics"].get("cycle_count", 0)
            
            # Update error count
            self.health_metrics["error_count"] += latest_data["metrics"].get("error_count", 0)
            
            # Update last update time
            self.health_metrics["last_update"] = datetime.utcnow()
    
    def _calculate_health_score(self, analysis_result: Dict, anomaly_result: Dict) -> int:
        """Calculate overall system health score (0-100)."""
        base_score = 100
        
        # Deduct points for active alerts
        active_alerts = self.health_metrics.get("active_alerts", [])
        for alert in active_alerts:
            if alert["severity"] == "critical":
                base_score -= 30
            elif alert["severity"] == "error":
                base_score -= 20
            elif alert["severity"] == "warning":
                base_score -= 10
            elif alert["severity"] == "info":
                base_score -= 5
        
        # Deduct points for anomalies
        anomalies = anomaly_result.get("anomalies", [])
        base_score -= len(anomalies) * 5
        
        # Deduct points for poor performance metrics
        metrics = analysis_result.get("metrics", {})
        if "cycle_time" in metrics and metrics["cycle_time"]["avg"] > 100:
            base_score -= 10
        
        if "error_rate" in metrics and metrics["error_rate"]["current"] > 0.05:
            base_score -= 15
        
        return max(0, min(100, base_score))
    
    def _determine_system_status(self, health_score: int) -> str:
        """Determine system status based on health score."""
        if health_score >= 90:
            return "excellent"
        elif health_score >= 75:
            return "good"
        elif health_score >= 60:
            return "fair"
        elif health_score >= 40:
            return "poor"
        else:
            return "critical"
    
    def _generate_health_recommendations(self, health_score: int, analysis_result: Dict) -> List[str]:
        """Generate health improvement recommendations."""
        recommendations = []
        
        if health_score < 70:
            recommendations.append("System health is below optimal - investigate active alerts")
        
        metrics = analysis_result.get("metrics", {})
        
        if "cycle_time" in metrics and metrics["cycle_time"]["avg"] > 100:
            recommendations.append("Optimize PLC program to reduce cycle time")
        
        if "memory_usage" in metrics and metrics["memory_usage"]["avg"] > 80:
            recommendations.append("Review memory usage and optimize data structures")
        
        if "error_rate" in metrics and metrics["error_rate"]["current"] > 0.01:
            recommendations.append("Investigate and resolve recurring errors")
        
        return recommendations
    
    def _get_highest_severity(self, alerts: List[Dict]) -> str:
        """Get the highest severity level from a list of alerts."""
        if not alerts:
            return "none"
        
        severity_order = {"critical": 4, "error": 3, "warning": 2, "info": 1}
        max_severity = max(alerts, key=lambda x: severity_order.get(x["severity"], 0))
        return max_severity["severity"]

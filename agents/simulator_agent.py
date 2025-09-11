"""Simulator agent for testing PLC code in virtual environments."""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from agents.base_agent import LLMAgent
from models.schemas import AgentRole, AgentTask, SimulationResult


class SimulatorAgent(LLMAgent):
    """Agent responsible for simulating and testing PLC code."""
    
    def __init__(self, llm=None):
        super().__init__(
            role=AgentRole.SIMULATOR,
            name="PLC Code Simulator",
            description="Simulates PLC code execution and validates behavior",
            llm=llm
        )
        
        # Simulation environments
        self.simulation_environments = {
            "basic": {
                "description": "Basic I/O simulation",
                "inputs": ["digital_inputs", "analog_inputs"],
                "outputs": ["digital_outputs", "analog_outputs"],
                "cycle_time": 10  # ms
            },
            "motor_control": {
                "description": "Motor control simulation",
                "inputs": ["start_button", "stop_button", "motor_feedback", "overload"],
                "outputs": ["motor_contactor", "status_led", "alarm"],
                "cycle_time": 50
            },
            "process_control": {
                "description": "Process control simulation",
                "inputs": ["temperature", "pressure", "flow_rate", "level"],
                "outputs": ["heater", "valve_position", "pump_speed"],
                "cycle_time": 100
            },
            "safety_system": {
                "description": "Safety system simulation",
                "inputs": ["emergency_stop", "light_curtain", "safety_door", "reset_button"],
                "outputs": ["safety_relay", "warning_light", "machine_enable"],
                "cycle_time": 5
            }
        }
        
        # Test scenarios
        self.test_scenarios = {
            "normal_operation": {
                "description": "Normal operating conditions",
                "duration": 30,  # seconds
                "input_patterns": "steady_state"
            },
            "startup_sequence": {
                "description": "System startup sequence",
                "duration": 60,
                "input_patterns": "sequential"
            },
            "emergency_stop": {
                "description": "Emergency stop activation",
                "duration": 15,
                "input_patterns": "emergency"
            },
            "fault_injection": {
                "description": "Fault condition testing",
                "duration": 45,
                "input_patterns": "fault_conditions"
            },
            "stress_test": {
                "description": "High-frequency input changes",
                "duration": 120,
                "input_patterns": "rapid_changes"
            }
        }
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the simulator agent."""
        return """
You are a PLC Code Simulator Agent specialized in testing IEC 61131-3 programs in virtual environments.

Your responsibilities:
1. Execute PLC code in simulated environments
2. Generate realistic input patterns and scenarios
3. Monitor outputs and system behavior
4. Validate functional requirements
5. Perform stress testing and fault injection
6. Generate comprehensive test reports

Simulation capabilities:
- Real-time I/O simulation
- Motor control systems
- Process control loops
- Safety system validation
- Performance benchmarking
- Fault condition testing

Test scenarios:
- Normal operation validation
- Startup/shutdown sequences
- Emergency stop testing
- Fault injection and recovery
- Stress testing under load
- Safety system verification

Always ensure thorough testing coverage and provide detailed analysis of system behavior.
"""
    
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        """Process a simulation task."""
        task_type = task.task_type
        input_data = task.input_data
        
        if task_type == "simulate_code":
            return await self._simulate_code(input_data)
        elif task_type == "run_test_scenario":
            return await self._run_test_scenario(input_data)
        elif task_type == "validate_functionality":
            return await self._validate_functionality(input_data)
        elif task_type == "stress_test":
            return await self._stress_test(input_data)
        elif task_type == "safety_test":
            return await self._safety_test(input_data)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _simulate_code(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate PLC code execution."""
        generated_code_data = input_data.get("previous_results", {}).get("generate_code", {})
        validation_results = input_data.get("previous_results", {}).get("validate_code", {})
        requirement = input_data.get("requirement", {})
        
        if not generated_code_data:
            raise ValueError("No generated code found for simulation")
        
        generated_code_obj = generated_code_data.get("generated_code", {})
        code = generated_code_obj.get("code", "")
        
        # Determine simulation environment
        environment = self._select_simulation_environment(code, requirement)
        
        # Run multiple test scenarios
        simulation_results = []
        
        for scenario_name in ["normal_operation", "startup_sequence", "fault_injection"]:
            if scenario_name in self.test_scenarios:
                scenario_result = await self._run_simulation_scenario(
                    code, environment, scenario_name
                )
                simulation_results.append(scenario_result)
        
        # Calculate overall results
        overall_success = all(result["success"] for result in simulation_results)
        total_test_time = sum(result["duration"] for result in simulation_results)
        
        return {
            "simulation_results": simulation_results,
            "overall_success": overall_success,
            "environment_used": environment,
            "total_test_time": total_test_time,
            "performance_metrics": self._calculate_performance_metrics(simulation_results),
            "recommendations": self._generate_simulation_recommendations(simulation_results),
            "simulated_at": datetime.utcnow().isoformat()
        }
    
    async def _run_test_scenario(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run a specific test scenario."""
        code = input_data.get("code", "")
        scenario_name = input_data.get("scenario", "normal_operation")
        environment = input_data.get("environment", "basic")
        
        result = await self._run_simulation_scenario(code, environment, scenario_name)
        
        return {
            "scenario_result": result,
            "scenario_name": scenario_name,
            "environment": environment
        }
    
    async def _validate_functionality(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate functional requirements through simulation."""
        code = input_data.get("code", "")
        requirements = input_data.get("requirements", [])
        
        validation_results = []
        
        for requirement in requirements:
            req_result = await self._validate_requirement(code, requirement)
            validation_results.append(req_result)
        
        overall_compliance = all(result["compliant"] for result in validation_results)
        
        return {
            "validation_results": validation_results,
            "overall_compliance": overall_compliance,
            "compliance_percentage": sum(1 for r in validation_results if r["compliant"]) / len(validation_results) * 100 if validation_results else 0
        }
    
    async def _stress_test(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform stress testing on the code."""
        code = input_data.get("code", "")
        duration = input_data.get("duration", 300)  # 5 minutes default
        
        stress_result = await self._run_simulation_scenario(
            code, "basic", "stress_test", duration
        )
        
        return {
            "stress_test_result": stress_result,
            "max_cycle_time": stress_result.get("max_cycle_time", 0),
            "memory_usage": stress_result.get("memory_usage", {}),
            "performance_degradation": stress_result.get("performance_degradation", False)
        }
    
    async def _safety_test(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform safety system testing."""
        code = input_data.get("code", "")
        safety_level = input_data.get("safety_level", 1)
        
        safety_scenarios = ["emergency_stop", "fault_injection"]
        safety_results = []
        
        for scenario in safety_scenarios:
            result = await self._run_simulation_scenario(
                code, "safety_system", scenario
            )
            safety_results.append(result)
        
        # Check safety compliance
        safety_compliance = self._check_safety_compliance(safety_results, safety_level)
        
        return {
            "safety_test_results": safety_results,
            "safety_compliance": safety_compliance,
            "sil_level_met": safety_compliance["sil_level_met"],
            "safety_violations": safety_compliance["violations"]
        }
    
    async def _run_simulation_scenario(
        self, 
        code: str, 
        environment: str, 
        scenario: str, 
        duration: Optional[int] = None
    ) -> Dict[str, Any]:
        """Run a specific simulation scenario."""
        
        # Get environment and scenario configuration
        env_config = self.simulation_environments.get(environment, self.simulation_environments["basic"])
        scenario_config = self.test_scenarios.get(scenario, self.test_scenarios["normal_operation"])
        
        test_duration = duration or scenario_config["duration"]
        cycle_time = env_config["cycle_time"]
        
        # Initialize simulation state
        simulation_state = {
            "inputs": {inp: False for inp in env_config["inputs"]},
            "outputs": {out: False for out in env_config["outputs"]},
            "cycle_count": 0,
            "start_time": datetime.utcnow(),
            "errors": [],
            "warnings": []
        }
        
        # Generate input patterns for the scenario
        input_patterns = await self._generate_input_patterns(
            scenario_config["input_patterns"], 
            env_config["inputs"], 
            test_duration
        )
        
        # Run simulation
        simulation_log = []
        max_cycle_time = 0
        
        for cycle in range(int(test_duration * 1000 / cycle_time)):
            cycle_start = datetime.utcnow()
            
            # Update inputs based on pattern
            if cycle < len(input_patterns):
                simulation_state["inputs"].update(input_patterns[cycle])
            
            # Execute PLC logic (simplified simulation)
            cycle_result = await self._execute_plc_cycle(
                code, simulation_state["inputs"], simulation_state["outputs"]
            )
            
            # Update outputs
            simulation_state["outputs"].update(cycle_result["outputs"])
            
            # Log cycle data
            cycle_time_ms = (datetime.utcnow() - cycle_start).total_seconds() * 1000
            max_cycle_time = max(max_cycle_time, cycle_time_ms)
            
            simulation_log.append({
                "cycle": cycle,
                "timestamp": cycle_start.isoformat(),
                "inputs": simulation_state["inputs"].copy(),
                "outputs": simulation_state["outputs"].copy(),
                "cycle_time_ms": cycle_time_ms,
                "errors": cycle_result.get("errors", [])
            })
            
            # Check for errors
            if cycle_result.get("errors"):
                simulation_state["errors"].extend(cycle_result["errors"])
            
            # Simulate cycle time delay
            await asyncio.sleep(cycle_time / 1000.0)
        
        # Analyze results
        end_time = datetime.utcnow()
        actual_duration = (end_time - simulation_state["start_time"]).total_seconds()
        
        success = len(simulation_state["errors"]) == 0
        
        return {
            "scenario": scenario,
            "environment": environment,
            "success": success,
            "duration": actual_duration,
            "cycle_count": len(simulation_log),
            "max_cycle_time": max_cycle_time,
            "errors": simulation_state["errors"],
            "warnings": simulation_state["warnings"],
            "final_outputs": simulation_state["outputs"],
            "performance_metrics": {
                "avg_cycle_time": sum(log["cycle_time_ms"] for log in simulation_log) / len(simulation_log) if simulation_log else 0,
                "max_cycle_time": max_cycle_time,
                "error_rate": len(simulation_state["errors"]) / len(simulation_log) if simulation_log else 0
            },
            "simulation_log": simulation_log[-100:] if len(simulation_log) > 100 else simulation_log  # Keep last 100 entries
        }
    
    async def _execute_plc_cycle(self, code: str, inputs: Dict[str, Any], current_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute one PLC cycle (simplified simulation)."""
        
        # This is a simplified simulation - in a real implementation,
        # you would parse and execute the actual ST code
        
        outputs = current_outputs.copy()
        errors = []
        
        try:
            # Simulate basic motor control logic
            if "start_button" in inputs and "stop_button" in inputs:
                if inputs["start_button"] and not inputs["stop_button"]:
                    outputs["motor_contactor"] = True
                    outputs["status_led"] = True
                elif inputs["stop_button"]:
                    outputs["motor_contactor"] = False
                    outputs["status_led"] = False
            
            # Simulate safety logic
            if "emergency_stop" in inputs:
                if inputs["emergency_stop"]:
                    # Emergency stop should turn off all outputs
                    for output_name in outputs:
                        if "safety" not in output_name.lower():
                            outputs[output_name] = False
                    outputs["warning_light"] = True
            
            # Simulate analog processing
            if "temperature" in inputs and isinstance(inputs["temperature"], (int, float)):
                if inputs["temperature"] > 80:
                    outputs["heater"] = False
                    outputs["alarm"] = True
                elif inputs["temperature"] < 70:
                    outputs["heater"] = True
                    outputs["alarm"] = False
            
            # Check for code-specific patterns
            if "safety_ok" in code.lower():
                # If code has safety logic, simulate safety checks
                safety_inputs = ["emergency_stop", "light_curtain", "safety_door"]
                safety_ok = all(not inputs.get(inp, False) for inp in safety_inputs if inp in inputs)
                
                if not safety_ok:
                    # Safety violation - turn off critical outputs
                    critical_outputs = ["motor_contactor", "heater", "pump_speed"]
                    for output in critical_outputs:
                        if output in outputs:
                            outputs[output] = False
            
        except Exception as e:
            errors.append(f"Simulation error: {str(e)}")
        
        return {
            "outputs": outputs,
            "errors": errors
        }
    
    async def _generate_input_patterns(self, pattern_type: str, input_names: List[str], duration: int) -> List[Dict[str, Any]]:
        """Generate input patterns for simulation."""
        
        cycles = int(duration * 20)  # 20 cycles per second (50ms cycle time)
        patterns = []
        
        if pattern_type == "steady_state":
            # Steady state - minimal changes
            base_pattern = {name: False for name in input_names}
            if "start_button" in input_names:
                base_pattern["start_button"] = True
            
            patterns = [base_pattern.copy() for _ in range(cycles)]
        
        elif pattern_type == "sequential":
            # Sequential activation
            for cycle in range(cycles):
                pattern = {name: False for name in input_names}
                
                # Activate inputs sequentially
                if cycle < len(input_names) * 10:
                    active_input = input_names[cycle // 10]
                    pattern[active_input] = True
                
                patterns.append(pattern)
        
        elif pattern_type == "emergency":
            # Emergency stop scenario
            for cycle in range(cycles):
                pattern = {name: False for name in input_names}
                
                # Normal operation for first half
                if cycle < cycles // 2:
                    if "start_button" in input_names:
                        pattern["start_button"] = True
                else:
                    # Emergency stop activation
                    if "emergency_stop" in input_names:
                        pattern["emergency_stop"] = True
                
                patterns.append(pattern)
        
        elif pattern_type == "fault_conditions":
            # Inject various fault conditions
            for cycle in range(cycles):
                pattern = {name: False for name in input_names}
                
                # Inject faults at different intervals
                if cycle % 50 == 0 and "overload" in input_names:
                    pattern["overload"] = True
                elif cycle % 75 == 0 and "light_curtain" in input_names:
                    pattern["light_curtain"] = True
                
                patterns.append(pattern)
        
        elif pattern_type == "rapid_changes":
            # Rapid input changes for stress testing
            for cycle in range(cycles):
                pattern = {}
                
                for name in input_names:
                    # Toggle inputs at different frequencies
                    if "button" in name.lower():
                        pattern[name] = (cycle % 5) == 0
                    else:
                        pattern[name] = (cycle % 3) == 0
                
                patterns.append(pattern)
        
        else:
            # Default pattern
            patterns = [{name: False for name in input_names} for _ in range(cycles)]
        
        return patterns
    
    async def _validate_requirement(self, code: str, requirement: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a specific functional requirement."""
        
        req_description = requirement.get("description", "")
        expected_behavior = requirement.get("expected_behavior", {})
        
        # Run a targeted test for this requirement
        test_result = await self._run_simulation_scenario(
            code, "basic", "normal_operation", 30
        )
        
        # Check if expected behavior is met
        compliant = True
        violations = []
        
        # Check output expectations
        final_outputs = test_result.get("final_outputs", {})
        for output_name, expected_value in expected_behavior.get("outputs", {}).items():
            if output_name in final_outputs:
                if final_outputs[output_name] != expected_value:
                    compliant = False
                    violations.append(f"Output {output_name} expected {expected_value}, got {final_outputs[output_name]}")
        
        # Check for errors
        if test_result.get("errors"):
            compliant = False
            violations.extend(test_result["errors"])
        
        return {
            "requirement": req_description,
            "compliant": compliant,
            "violations": violations,
            "test_result": test_result
        }
    
    def _select_simulation_environment(self, code: str, requirement: Dict[str, Any]) -> str:
        """Select appropriate simulation environment based on code and requirements."""
        
        code_lower = code.lower()
        description = requirement.get("description", "").lower()
        
        if any(keyword in code_lower or keyword in description 
               for keyword in ["motor", "pump", "fan", "drive"]):
            return "motor_control"
        elif any(keyword in code_lower or keyword in description 
                 for keyword in ["temperature", "pressure", "flow", "level"]):
            return "process_control"
        elif any(keyword in code_lower or keyword in description 
                 for keyword in ["safety", "emergency", "interlock"]):
            return "safety_system"
        else:
            return "basic"
    
    def _calculate_performance_metrics(self, simulation_results: List[Dict]) -> Dict[str, Any]:
        """Calculate overall performance metrics."""
        
        if not simulation_results:
            return {}
        
        total_cycles = sum(result.get("cycle_count", 0) for result in simulation_results)
        total_errors = sum(len(result.get("errors", [])) for result in simulation_results)
        avg_cycle_times = [result.get("performance_metrics", {}).get("avg_cycle_time", 0) 
                          for result in simulation_results]
        
        return {
            "total_test_cycles": total_cycles,
            "total_errors": total_errors,
            "error_rate": total_errors / total_cycles if total_cycles > 0 else 0,
            "avg_cycle_time": sum(avg_cycle_times) / len(avg_cycle_times) if avg_cycle_times else 0,
            "max_cycle_time": max((result.get("max_cycle_time", 0) for result in simulation_results), default=0),
            "success_rate": sum(1 for result in simulation_results if result.get("success", False)) / len(simulation_results) * 100
        }
    
    def _generate_simulation_recommendations(self, simulation_results: List[Dict]) -> List[str]:
        """Generate recommendations based on simulation results."""
        
        recommendations = []
        
        # Check for performance issues
        performance_metrics = self._calculate_performance_metrics(simulation_results)
        
        if performance_metrics.get("error_rate", 0) > 0.01:  # More than 1% error rate
            recommendations.append("High error rate detected - review code logic and error handling")
        
        if performance_metrics.get("max_cycle_time", 0) > 100:  # More than 100ms cycle time
            recommendations.append("Long cycle times detected - consider code optimization")
        
        if performance_metrics.get("success_rate", 100) < 90:
            recommendations.append("Low success rate - investigate failing scenarios")
        
        # Check for safety issues
        safety_results = [result for result in simulation_results 
                         if "emergency" in result.get("scenario", "")]
        
        if safety_results:
            for result in safety_results:
                if not result.get("success", False):
                    recommendations.append("Safety scenario failed - review emergency stop logic")
        
        return recommendations
    
    def _check_safety_compliance(self, safety_results: List[Dict], safety_level: int) -> Dict[str, Any]:
        """Check safety compliance based on SIL level."""
        
        violations = []
        sil_requirements_met = True
        
        # Check emergency stop response time
        for result in safety_results:
            if "emergency" in result.get("scenario", ""):
                # Emergency stop should activate within 1 second for SIL 2+
                if safety_level >= 2:
                    response_time = result.get("duration", 0)
                    if response_time > 1.0:
                        violations.append("Emergency stop response time exceeds 1 second")
                        sil_requirements_met = False
        
        # Check for safety output behavior
        for result in safety_results:
            final_outputs = result.get("final_outputs", {})
            
            # Safety outputs should be in safe state during emergency
            if "emergency" in result.get("scenario", ""):
                critical_outputs = ["motor_contactor", "heater", "pump_speed"]
                for output in critical_outputs:
                    if final_outputs.get(output, False):
                        violations.append(f"Critical output {output} not in safe state during emergency")
                        sil_requirements_met = False
        
        return {
            "sil_level_met": sil_requirements_met,
            "target_sil": safety_level,
            "violations": violations,
            "compliance_score": 100 if sil_requirements_met else max(0, 100 - len(violations) * 20)
        }

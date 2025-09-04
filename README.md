AutoPLC - AI-Powered PLC Code Generation

🚀 Advanced Multi-Agent System for IEC 61131-3 Structured Text Code Generation

AutoPLC is a cutting-edge hackathon project that uses multiple specialized AI agents to generate, validate, and simulate PLC code from natural language descriptions. Built with NVIDIA NIM API and modern web technologies.
✨ Features
🤖 Multi-Agent Architecture

    Planner Agent: Creates detailed implementation plans (Llama 3.1-70B)

    Coder Agent: Generates syntactically correct ST code (Llama 3.1-70B)

    Validator Agent: Compiles and lints code (Mistral-7B)

    Knowledge Agent: Provides IEC standards expertise (Phi-4-Mini)

    Retrieval Agent: Searches technical documentation (Mistral-7B)

    Simulator Agent: Integrates with OpenPLC/ScadaBR

🎯 Smart Model Routing

    High-Performance Models (Llama 3.1-70B) for complex reasoning and code generation

    Efficient Models (Mistral-7B, Phi-4-Mini) for tool calling and quick responses

    Automatic Fallback between primary and secondary API keys

    Role-Based Optimization for maximum accuracy and speed

💻 Modern UI/UX

    Real-Time Agent Chat: Watch agents collaborate in real-time

    Syntax Highlighting: Professional ST code viewer

    Live Simulation: Integration with OpenPLC Runtime

    Mobile Responsive: Works perfectly on all devices

    Professional Design: Clean, modern interface

🔧 Production Features

    MATIEC Compiler Integration: Real syntax validation

    Knowledge Base: RAG with PDF documentation

    Error Recovery: Automatic code fixing and optimization

    Simulation Workflow: Complete OpenPLC/ScadaBR integration

    API Rate Limiting: Production-ready request handling

🏗 Architecture

┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Modern UI     │    │  Enhanced Flask  │    │  NVIDIA NIM     │
│   (React-like)  │◄──►│     Backend      │◄──►│   API Cluster   │
│_________________│    │__________________|    |_________________|

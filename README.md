AutoPLC - AI-Powered PLC Code Generation

🚀 Advanced Multi-Agent System for IEC 61131-3 Structured Text Code Generation

AutoPLC is a cutting-edge hackathon project that uses multiple specialized AI agents to generate, validate, and simulate PLC code from natural language descriptions. Built with NVIDIA NIM API and modern web technologies.
✨ Features
🤖 Multi-Agent Architecture

    Planner Agent: Creates detailed implementation plans (openai/gpt-oss-120b)

    Coder Agent: Generates highly specialized ST code (qwen/qwen3-coder-480b-a35b-instruct)

    Validator Agent: Compiles and validates code with high accuracy (nvidia/llama-3.1-nemotron-ultra-253b-v1)

    Knowledge Agent: Synthesizes expert IEC knowledge (nvidia/llama-3.1-nemotron-ultra-253b-v1)

    Retrieval Agent: Searches and synthesizes external documentation (nvidia/llama-3.1-nemotron-ultra-253b-v1)

    Simulator Agent: Integrates with OpenPLC/ScadaBR

🎯 Smart Model Routing

    High-Performance Models (Qwen, Nemotron Ultra) for complex reasoning and code generation

    Efficient Models (Nemotron Nano) for tool calling and quick fallback responses

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

    Knowledge Base: RAG with Markdown and source code from `knowledge_base/documents`

    Error Recovery: Automatic code fixing and optimization

    Simulation Workflow: Complete OpenPLC/ScadaBR integration

    API Rate Limiting: Production-ready request handling

🏗 Architecture

┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Modern UI     │    │   FastAPI Backend  │    │  NVIDIA NIM     │
│   (React-like)  │◄──►│ (Uvicorn Server) │◄──►│   API Cluster   │
│_________________│    │__________________|    |_________________|

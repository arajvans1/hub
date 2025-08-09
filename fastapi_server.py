#!/usr/bin/env python3
"""
FastAPI Server - Step 1: Basic Setup

Starting simple, just like our native HTTP server.
We'll add features one by one to see what FastAPI automates.
"""

from fastapi import FastAPI
from llm import SharedResources, SAPMonitoringAgent

# Global components (same as native server)
shared_resources = None
monitoring_agent = None

def initialize_components():
    """Initialize components (exactly like native server)."""
    global shared_resources, monitoring_agent
    try:
        shared_resources = SharedResources()
        shared_resources.initialize()
        monitoring_agent = SAPMonitoringAgent(shared_resources)
        return True
    except Exception as e:
        print(f"Failed to initialize: {e}")
        return False

# 🚀 CREATE BASIC FASTAPI APP
app = FastAPI(
    title="SAP Monitoring Chat API - Step 1",
    description="Basic FastAPI setup, no fancy features yet",
    version="1.0.0"
)

# 🎯 BASIC CHAT ENDPOINT - Compare to our native version
@app.post("/chat")
async def chat_endpoint(request: dict):
    """
    Step 1: Basic endpoint with manual everything
    Just like our native server, but with FastAPI routing
    """
    try:
        # Manual validation (just like native server)
        message = request.get("message", "").strip()
        if not message:
            return {"error": "Message required"}
        
        chat_history = request.get("chat_history", [])
        
        # Add system prompt if needed
        if not chat_history:
            chat_history = [{"role": "system", "content": monitoring_agent.system_prompt}]
        
        # Add user message
        chat_history.append({"role": "user", "content": message})
        
        # Get AI response (still blocking, like native server)
        response = monitoring_agent.chat(chat_history)
        
        # Simple response (no structure yet)
        return {
            "response": response,
            "chat_history": chat_history
        }
        
    except Exception as e:
        return {"error": f"Chat error: {str(e)}"}

# 📚 COMPARISON PAGE
@app.get("/")
async def home():
    """Simple comparison page"""
    return {
        "message": "FastAPI Step 1: Basic Setup",
        "features": {
            "current": ["Basic routing", "Simple JSON responses"],
            "missing": ["Request validation", "Response models", "Logging", "Documentation", "Async"],
            "next_step": "Add Pydantic request validation"
        },
        "endpoints": {
            "POST /chat": "Basic chat endpoint",
            "GET /": "This status page"
        }
    }

# 🏃‍♂️ STARTUP
@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    if not initialize_components():
        raise RuntimeError("Failed to initialize components")

# 🛠️ RUN SERVER
if __name__ == "__main__":
    import uvicorn
    
    print("FastAPI Step 1: Basic Setup - http://localhost:8000")
    
    uvicorn.run(
        "fastapi_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

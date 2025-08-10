#!/usr/bin/env python3
"""
FastAPI Server for SAP Monitoring Chat API
Essential endpoints and static file serving only.
"""

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from llm import SharedResources, SAPMonitoringAgent

shared_resources = None
monitoring_agent = None

def initialize_components():
    global shared_resources, monitoring_agent
    try:
        shared_resources = SharedResources()
        shared_resources.initialize()
        monitoring_agent = SAPMonitoringAgent(shared_resources)
        return True
    except Exception as e:
        print(f"Failed to initialize: {e}")
        return False

app = FastAPI(title="SAP Monitoring Chat API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")



# --- Chat API ---
@app.post("/chat")
async def chat_endpoint(request: dict):
    try:
        message = request.get("message", "").strip()
        if not message:
            return {"error": "Message required"}
        chat_history = request.get("chat_history", [])
        if not chat_history:
            chat_history = [{"role": "system", "content": monitoring_agent.system_prompt}]
        chat_history.append({"role": "user", "content": message})
        response = monitoring_agent.chat(chat_history)
        return {"response": response, "chat_history": chat_history}
    except Exception as e:
        return {"error": f"Chat error: {str(e)}"}

# --- Serve index.html at root ---
@app.get("/")
async def serve_index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"error": "index.html not found"}

@app.on_event("startup")
async def startup_event():
    if not initialize_components():
        raise RuntimeError("Failed to initialize components")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "fastapi_server:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )

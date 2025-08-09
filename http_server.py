#!/usr/bin/env python3
"""
Simple HTTP Server for SAP S/4HANA Monitoring Platform
Just one endpoint: POST /chat
"""

import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from llm import SharedResources, SAPMonitoringAgent

# Global components
shared_resources = None
monitoring_agent = None


def initialize_components():
    """Initialize components."""
    global shared_resources, monitoring_agent
    try:
        shared_resources = SharedResources()
        shared_resources.initialize()
        monitoring_agent = SAPMonitoringAgent(shared_resources)
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


class ChatHandler(BaseHTTPRequestHandler):
    """Simple chat handler."""
    
    def log_message(self, format, *args):
        """
        LEARNING: Custom request logging
        (FastAPI will have built-in logging middleware)
        """
        timestamp = time.strftime('%H:%M:%S')
        client_ip = self.address_string()
        print(f"[{timestamp}] {client_ip} - {format % args}")
    
    def do_OPTIONS(self):
        """Handle CORS."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        """
        LEARNING: Manual API documentation
        (FastAPI will auto-generate OpenAPI/Swagger docs)
        """
        request_id = f"req_{int(time.time() * 1000) % 10000}"
        path = urlparse(self.path).path
        
        print(f"🔵 [{request_id}] GET {path}")
        
        if path == '/' or path == '/docs':
            self._send_api_docs(request_id)
        elif path == '/openapi.json':
            self._send_openapi_schema(request_id)
        else:
            self._send_error("Available: GET / (docs), GET /openapi.json (schema), POST /chat", 404, request_id)
    
    def do_POST(self):
        """Handle POST requests."""
        # LEARNING: Manual request timing and logging (FastAPI middleware will do this)
        start_time = time.time()
        request_id = f"req_{int(time.time() * 1000) % 10000}"  # Simple request ID
        client_ip = self.address_string()
        
        print(f"🔵 [{request_id}] POST {self.path} from {client_ip}")
        
        if urlparse(self.path).path != '/chat':
            self._send_error("Only /chat endpoint available", 404, request_id)
            return
        
        try:
            # MANUAL REQUEST VALIDATION (what FastAPI will do automatically)
            request_data = self._validate_chat_request(request_id)
            if not request_data:
                return  # Error already sent
            
            message = request_data["message"]
            chat_history = request_data["chat_history"]
            
            print(f"📝 [{request_id}] Processing message: '{message[:50]}{'...' if len(message) > 50 else ''}'")
            
            # Add system prompt if needed
            if not chat_history:
                chat_history = [{"role": "system", "content": monitoring_agent.system_prompt}]
            
            # Add user message
            chat_history.append({"role": "user", "content": message})
            
            # Time the AI response
            ai_start_time = time.time()
            # 🐘 ELEPHANT IN THE ROOM: This blocks the entire server!
            # While waiting for AI response, NO other requests can be processed
            response = monitoring_agent.chat(chat_history)
            ai_duration = (time.time() - ai_start_time) * 1000
            
            print(f"🤖 [{request_id}] AI response generated in {ai_duration:.1f}ms")
            
            # STRUCTURED RESPONSE (what FastAPI will enforce with response models)
            structured_response = self._create_success_response(
                response=response,
                chat_history=chat_history,
                message_count=len(chat_history),
                request_id=request_id
            )
            
            # Send response
            self._send_json(structured_response)
            
            # Log successful completion
            total_duration = (time.time() - start_time) * 1000
            print(f"✅ [{request_id}] Request completed in {total_duration:.1f}ms (AI: {ai_duration:.1f}ms)")
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            print(f"❌ [{request_id}] Request failed after {duration:.1f}ms: {str(e)}")
            self._send_error(f"Error: {str(e)}", 500, request_id)
    
    def _validate_chat_request(self, request_id: str):
        """
        LEARNING: Manual request validation 
        (FastAPI will do this automatically with Pydantic models)
        """
        try:
            # Parse JSON body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_error("Request body required", 400, request_id)
                return None
                
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            print(f"📥 [{request_id}] Received {content_length} bytes of JSON data")
            
            # Validate required field: message
            message = data.get("message", "").strip()
            if not message:
                self._send_error("Field 'message' is required and cannot be empty", 400, request_id)
                return None
            
            if len(message) > 1000:
                self._send_error("Field 'message' cannot exceed 1000 characters", 400, request_id)
                return None
            
            # Validate optional field: chat_history
            chat_history = data.get("chat_history", [])
            if not isinstance(chat_history, list):
                self._send_error("Field 'chat_history' must be an array", 400, request_id)
                return None
            
            # Validate chat_history structure
            for i, msg in enumerate(chat_history):
                if not isinstance(msg, dict):
                    self._send_error(f"chat_history[{i}] must be an object", 400, request_id)
                    return None
                if "role" not in msg or "content" not in msg:
                    self._send_error(f"chat_history[{i}] must have 'role' and 'content'", 400, request_id)
                    return None
            
            print(f"✅ [{request_id}] Validation passed: message={len(message)} chars, history={len(chat_history)} messages")
            return {"message": message, "chat_history": chat_history}
            
        except json.JSONDecodeError as e:
            self._send_error(f"Invalid JSON: {str(e)}", 400, request_id)
            return None
        except Exception as e:
            self._send_error(f"Request validation error: {str(e)}", 400, request_id)
            return None
    
    def _create_success_response(self, response: str, chat_history: list, message_count: int, request_id: str):
        """
        LEARNING: Structured response models
        (FastAPI will enforce this with Pydantic response models)
        """
        from datetime import datetime
        
        # Standard success response structure
        return {
            "success": True,
            "data": {
                "response": response,
                "chat_history": chat_history
            },
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "message_count": message_count,
                "response_length": len(response),
                "server_version": "1.0.0",
                "request_id": request_id
            }
        }
    
    def _create_error_response(self, message: str, code: int, details: str = None):
        """
        LEARNING: Structured error response models
        (FastAPI will standardize this with exception handlers)
        """
        from datetime import datetime
        
        error_response = {
            "success": False,
            "error": {
                "message": message,
                "code": code,
                "type": "validation_error" if code == 400 else "server_error"
            },
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "server_version": "1.0.0"
            }
        }
        
        if details:
            error_response["error"]["details"] = details
            
            return error_response
    
    def _send_api_docs(self, request_id: str):
        """
        LEARNING: Manual API documentation
        (FastAPI will auto-generate beautiful Swagger UI)
        """
        docs_html = """
<!DOCTYPE html>
<html>
<head>
    <title>SAP Monitoring Chat API - Documentation</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
        .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .method { display: inline-block; padding: 4px 8px; border-radius: 3px; color: white; font-weight: bold; }
        .post { background: #49cc90; }
        .get { background: #61affe; }
        code { background: #f0f0f0; padding: 2px 4px; border-radius: 3px; }
        pre { background: #f8f8f8; padding: 10px; border-radius: 5px; overflow-x: auto; }
    </style>
</head>
<body>
    <h1>🚀 SAP Monitoring Chat API</h1>
    <p><strong>Version:</strong> 1.0.0 | <strong>Server:</strong> Native HTTP | <strong>Request ID:</strong> {request_id}</p>
    
    <h2>📋 Available Endpoints</h2>
    
    <div class="endpoint">
        <h3><span class="method post">POST</span> /chat</h3>
        <p><strong>Description:</strong> Chat with SAP monitoring assistant</p>
        
        <h4>Request Body (JSON):</h4>
        <pre><code>{{
  "message": "string (required, 1-1000 chars)",
  "chat_history": [
    {{
      "role": "user|assistant|system",
      "content": "string"
    }}
  ] (optional)
}}</code></pre>

        <h4>Response (JSON):</h4>
        <pre><code>{{
  "success": true,
  "data": {{
    "response": "AI assistant response",
    "chat_history": [...]
  }},
  "metadata": {{
    "timestamp": "2025-01-08T10:30:00Z",
    "message_count": 3,
    "response_length": 145,
    "server_version": "1.0.0",
    "request_id": "req_1234"
  }}
}}</code></pre>

        <h4>Example Request:</h4>
        <pre><code>curl -X POST http://localhost:8080/chat \\
  -H "Content-Type: application/json" \\
  -d '{{"message": "Show me available SAP systems"}}'</code></pre>
    </div>
    
    <div class="endpoint">
        <h3><span class="method get">GET</span> /</h3>
        <p><strong>Description:</strong> This documentation page</p>
    </div>
    
    <div class="endpoint">
        <h3><span class="method get">GET</span> /openapi.json</h3>
        <p><strong>Description:</strong> OpenAPI schema (machine-readable)</p>
    </div>
    
    <h2>🔧 Error Responses</h2>
    <p>All errors follow this structure:</p>
    <pre><code>{{
  "success": false,
  "error": {{
    "message": "Error description",
    "code": 400,
    "type": "validation_error|server_error"
  }},
  "metadata": {{
    "timestamp": "2025-01-08T10:30:00Z",
    "server_version": "1.0.0"
  }}
}}</code></pre>
    
    <h2>📊 Common Error Codes</h2>
    <ul>
        <li><strong>400:</strong> Bad Request (validation errors)</li>
        <li><strong>404:</strong> Endpoint not found</li>
        <li><strong>500:</strong> Internal server error</li>
    </ul>
    
    <footer style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666;">
        <p>Generated manually by native HTTP server | FastAPI will auto-generate this!</p>
    </footer>
</body>
</html>
        """.format(request_id=request_id)
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(docs_html.encode('utf-8'))
        
        print(f"📚 [{request_id}] Served API documentation")
    
    def _send_openapi_schema(self, request_id: str):
        """
        LEARNING: Manual OpenAPI schema
        (FastAPI will auto-generate this from your code)
        """
        openapi_schema = {
            "openapi": "3.0.0",
            "info": {
                "title": "SAP Monitoring Chat API",
                "description": "Chat interface for SAP S/4HANA monitoring platform",
                "version": "1.0.0"
            },
            "paths": {
                "/chat": {
                    "post": {
                        "summary": "Chat with SAP monitoring assistant",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["message"],
                                        "properties": {
                                            "message": {
                                                "type": "string",
                                                "minLength": 1,
                                                "maxLength": 1000,
                                                "description": "User message to the AI assistant"
                                            },
                                            "chat_history": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "required": ["role", "content"],
                                                    "properties": {
                                                        "role": {"type": "string", "enum": ["user", "assistant", "system"]},
                                                        "content": {"type": "string"}
                                                    }
                                                },
                                                "description": "Previous chat messages"
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "description": "Successful chat response",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "success": {"type": "boolean"},
                                                "data": {
                                                    "type": "object",
                                                    "properties": {
                                                        "response": {"type": "string"},
                                                        "chat_history": {"type": "array"}
                                                    }
                                                },
                                                "metadata": {"type": "object"}
                                            }
                                        }
                                    }
                                }
                            },
                            "400": {"description": "Validation error"},
                            "500": {"description": "Server error"}
                        }
                    }
                }
            }
        }
        
        self._send_json(openapi_schema)
        print(f"🔧 [{request_id}] Served OpenAPI schema")
    
    def _send_json(self, data):
        """Send JSON response."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def _send_error(self, message, code, request_id: str = "unknown"):
        """Send structured error response."""
        error_response = self._create_error_response(message, code)
        
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(error_response, indent=2).encode('utf-8'))
        
        print(f"❌ [{request_id}] Error {code}: {message}")


if __name__ == '__main__':
    print("🚀 SAP Monitoring HTTP Server")
    
    if initialize_components():
        print("✅ Components initialized")
        print("📋 Endpoint: POST /chat")
        print("🌐 Starting on http://localhost:8080")
        
        httpd = HTTPServer(('0.0.0.0', 8080), ChatHandler)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server stopped")
    else:
        print("❌ Failed to initialize")

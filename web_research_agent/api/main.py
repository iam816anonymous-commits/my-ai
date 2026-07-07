import asyncio
import json
import logging
from typing import List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from web_research_agent.agents.researcher import ResearchAgent
from web_research_agent.tools.storage import storage
from web_research_agent.config import OUTPUT_DIR, LOG_LEVEL
from web_research_agent.startup import initialize_directories, setup_logging

# Initialize system
initialize_directories()
setup_logging()

logger = logging.getLogger(__name__)

app = FastAPI(title="Web Research Platform API")

from web_research_agent.models.schemas import ResearchRequest

# CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

@app.get("/health")
def health_check():
    from web_research_agent.startup import run_health_check
    return {
        "status": "ok" if run_health_check() else "unhealthy",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/reports")
def get_reports():
    return storage.get_history()

@app.get("/reports/{report_id}")
def get_report(report_id: str):
    report_path = storage.get_report_path(report_id)
    if not report_path:
        raise HTTPException(status_code=404, detail="Report not found")

    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Try to load associated JSON for richer data
    json_path = OUTPUT_DIR / "exports" / "json" / f"{report_id}.json"
    data = {}
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

    return {"id": report_id, "content": content, "data": data}

@app.websocket("/ws/research")
async def websocket_research(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            request = ResearchRequest.model_validate_json(data)

            # Setup agent with progress callback
            queue = asyncio.Queue()
            loop = asyncio.get_running_loop()

            def on_progress(event_type, state_data):
                # We need to bridge thread/sync to async using captured loop
                loop.call_soon_threadsafe(queue.put_nowait, json.dumps({"event": event_type, "state": state_data}))

            agent = ResearchAgent(on_progress=on_progress)

            # Run agent in thread to not block event loop
            def run_agent():
                try:
                    agent.run(request.query)
                except Exception as e:
                    logger.exception(f"Agent thread error: {e}")
                    # We must use the loop from the closure
                    loop.call_soon_threadsafe(queue.put_nowait, json.dumps({
                        "event": "error",
                        "message": str(e),
                        "timestamp": datetime.now().isoformat()
                    }))
                finally:
                    loop.call_soon_threadsafe(queue.put_nowait, None) # Sentinel

            loop = asyncio.get_running_loop()
            # Start agent in background thread
            agent_task = loop.run_in_executor(None, run_agent)

            # Process queue as events come in (streaming)
            while True:
                msg = await queue.get()
                if msg is None: break
                await websocket.send_text(msg)

            # Wait for thread completion
            await agent_task
            await websocket.send_text(json.dumps({"event": "complete"}))

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

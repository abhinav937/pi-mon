#!/usr/bin/env python3
"""
Pi Monitor - Main FastAPI Server
Real-time Raspberry Pi monitoring dashboard backend with MQTT, WebSocket, and REST API
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import redis.asyncio as redis
import socketio
import structlog
from fastapi import FastAPI, HTTPException, Depends, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi_mqtt import FastMQTT, MQTTConfig
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv

from system_monitor import SystemMonitor
from power_management import PowerManager
from service_management import ServiceManager
from config import get_config

# Load configuration
config = get_config()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Configuration (using centralized config)
JWT_SECRET = config.jwt_secret
JWT_ALGORITHM = config.jwt_algorithm
JWT_EXPIRATION_HOURS = config.jwt_expiration_hours
MQTT_BROKER = config.mqtt_broker
MQTT_PORT = config.mqtt_port
REDIS_URL = config.redis_url
BACKEND_PORT = config.backend_port

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Pydantic models
class SystemStats(BaseModel):
    timestamp: str
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    temperature: float
    uptime: str
    network: Dict[str, int]

class PowerAction(BaseModel):
    action: str  # "shutdown" or "restart"
    delay: Optional[int] = 0

class ServiceAction(BaseModel):
    service_name: str
    action: str  # "start", "stop", "restart", "status"

class AuthResponse(BaseModel):
    access_token: str
    token_type: str

# FastAPI app initialization
app = FastAPI(
    title="Pi Monitor API",
    description="Real-time Raspberry Pi monitoring system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SocketIO integration
sio = socketio.AsyncServer(
    cors_allowed_origins="*",
    async_mode="asgi"
)

# Combine FastAPI and SocketIO
combined_app = socketio.ASGIApp(sio, app)

# MQTT configuration
mqtt_config = MQTTConfig(
    host=MQTT_BROKER,
    port=MQTT_PORT,
    keepalive=config.mqtt_keepalive,
    username=config.mqtt_username,
    password=config.mqtt_password
)

mqtt = FastMQTT(config=mqtt_config)

# Initialize components
system_monitor = SystemMonitor()
power_manager = PowerManager()
service_manager = ServiceManager()
redis_client = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket client connected", total_connections=len(self.active_connections))
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("WebSocket client disconnected", total_connections=len(self.active_connections))
    
    async def broadcast(self, data: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(data))
            except Exception as e:
                logger.warning("Failed to send data to WebSocket client", error=str(e))
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

# JWT functions
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return username
    except JWTError:
        raise credentials_exception

# Redis functions
async def get_cached_data(key: str) -> Optional[dict]:
    if redis_client:
        try:
            data = await redis_client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.warning("Redis get error", key=key, error=str(e))
    return None

async def cache_data(key: str, data: dict, ttl: int = 3600):
    if redis_client:
        try:
            await redis_client.setex(key, ttl, json.dumps(data))
        except Exception as e:
            logger.warning("Redis set error", key=key, error=str(e))

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    global redis_client
    logger.info("Starting Pi Monitor backend server")
    
    # Initialize Redis
    try:
        redis_client = redis.from_url(REDIS_URL)
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error("Redis connection failed", error=str(e))
    
    # Initialize MQTT
    mqtt.init_app(app)
    logger.info("MQTT initialized")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Pi Monitor backend server")
    if redis_client:
        await redis_client.close()

# MQTT event handlers
@mqtt.on_connect()
def connect(client, flags, rc, properties):
    logger.info("MQTT connected", return_code=rc)
    # Subscribe to Pi metrics topics
    topics = ["/pi/cpu", "/pi/memory", "/pi/disk", "/pi/temperature", "/pi/network"]
    for topic in topics:
        mqtt.client.subscribe(topic)
        logger.info("Subscribed to MQTT topic", topic=topic)

@mqtt.on_message()
async def message(client, topic, payload, qos, properties):
    try:
        data = json.loads(payload.decode())
        logger.debug("MQTT message received", topic=topic, data=data)
        
        # Cache the data
        cache_key = f"mqtt:{topic.replace('/', ':')}"
        await cache_data(cache_key, data, ttl=300)  # 5 minutes
        
        # Broadcast to WebSocket clients
        broadcast_data = {
            "type": "mqtt_update",
            "topic": topic,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await manager.broadcast(broadcast_data)
        
        # Emit to SocketIO clients
        await sio.emit("system_update", broadcast_data)
        
    except json.JSONDecodeError as e:
        logger.error("Invalid MQTT message format", topic=topic, payload=payload.decode(), error=str(e))
    except Exception as e:
        logger.error("Error processing MQTT message", topic=topic, error=str(e))

# SocketIO event handlers
@sio.event
async def connect(sid, environ):
    logger.info("SocketIO client connected", sid=sid)
    
    # Send initial system stats
    try:
        stats = await system_monitor.get_system_stats()
        await sio.emit("system_update", {"type": "initial_stats", "data": stats}, room=sid)
    except Exception as e:
        logger.error("Error sending initial stats", error=str(e))

@sio.event
async def disconnect(sid):
    logger.info("SocketIO client disconnected", sid=sid)

# REST API endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.post("/api/auth/token", response_model=AuthResponse)
async def login():
    """Simple authentication endpoint (for demo purposes)"""
    # In production, implement proper user authentication
    access_token = create_access_token(data={"sub": "pi-monitor"})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/system", response_model=SystemStats)
async def get_system_stats(current_user: str = Depends(get_current_user)):
    """Get current system statistics"""
    try:
        # Try to get from cache first
        cached = await get_cached_data("system:stats")
        if cached:
            return SystemStats(**cached)
        
        # Get fresh data
        stats = await system_monitor.get_system_stats()
        
        # Cache the data
        await cache_data("system:stats", stats.dict(), ttl=60)  # 1 minute
        
        return stats
    except Exception as e:
        logger.error("Error getting system stats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get system stats")

@app.post("/api/power")
async def power_action(action: PowerAction, current_user: str = Depends(get_current_user)):
    """Execute power management actions (shutdown/restart)"""
    try:
        result = await power_manager.execute_action(action.action, action.delay)
        logger.info("Power action executed", action=action.action, delay=action.delay)
        return {"success": True, "message": result}
    except Exception as e:
        logger.error("Power action failed", action=action.action, error=str(e))
        raise HTTPException(status_code=500, detail=f"Power action failed: {str(e)}")

@app.get("/api/services")
async def get_services(current_user: str = Depends(get_current_user)):
    """Get list of system services and their status"""
    try:
        services = await service_manager.get_services_status()
        return {"services": services}
    except Exception as e:
        logger.error("Error getting services", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get services")

@app.post("/api/services")
async def service_action(action: ServiceAction, current_user: str = Depends(get_current_user)):
    """Execute service management actions"""
    try:
        result = await service_manager.execute_action(action.service_name, action.action)
        logger.info("Service action executed", service=action.service_name, action=action.action)
        return {"success": True, "message": result}
    except Exception as e:
        logger.error("Service action failed", service=action.service_name, action=action.action, error=str(e))
        raise HTTPException(status_code=500, detail=f"Service action failed: {str(e)}")

# WebSocket endpoint
@app.websocket("/ws/system-stats")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial system stats
        stats = await system_monitor.get_system_stats()
        await websocket.send_text(json.dumps({
            "type": "initial_stats",
            "data": stats.dict(),
            "timestamp": datetime.utcnow().isoformat()
        }))
        
        # Keep connection alive
        while True:
            try:
                # Wait for messages from client (heartbeat)
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if message == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send periodic updates if no client messages
                stats = await system_monitor.get_system_stats()
                await websocket.send_text(json.dumps({
                    "type": "periodic_update",
                    "data": stats.dict(),
                    "timestamp": datetime.utcnow().isoformat()
                }))
            except WebSocketDisconnect:
                break
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
    finally:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    
    # Run the server
    uvicorn.run(
        combined_app,
        host=config.backend_host,
        port=config.backend_port,
        log_level=config.log_level,
        access_log=True
    )

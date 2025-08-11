#!/usr/bin/env python3
"""
Pi Monitor - Configuration Management
Centralized configuration system for all Pi Monitor settings
"""

import os
from typing import Optional
from pydantic import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class PiMonitorConfig(BaseSettings):
    """
    Pi Monitor configuration settings
    All settings can be overridden via environment variables
    """
    
    # Server Configuration
    backend_port: int = 5001
    backend_host: str = "0.0.0.0"
    frontend_port: int = 80
    
    # Database Configuration
    redis_url: str = "redis://localhost:6379"
    
    # MQTT Configuration
    mqtt_broker: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None
    mqtt_keepalive: int = 60
    
    # Security Configuration
    jwt_secret: str = "your-super-secret-jwt-key"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # Monitoring Configuration
    publish_interval: float = 5.0
    device_name: str = "raspberry-pi"
    
    # Log Configuration
    log_level: str = "info"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        # Map environment variable names to field names
        fields = {
            "backend_port": {"env": "BACKEND_PORT"},
            "backend_host": {"env": "BACKEND_HOST"},
            "frontend_port": {"env": "FRONTEND_PORT"},
            "redis_url": {"env": "REDIS_URL"},
            "mqtt_broker": {"env": "MQTT_BROKER"},
            "mqtt_port": {"env": "MQTT_PORT"},
            "mqtt_username": {"env": "MQTT_USERNAME"},
            "mqtt_password": {"env": "MQTT_PASSWORD"},
            "mqtt_keepalive": {"env": "MQTT_KEEPALIVE"},
            "jwt_secret": {"env": "JWT_SECRET"},
            "jwt_algorithm": {"env": "JWT_ALGORITHM"},
            "jwt_expiration_hours": {"env": "JWT_EXPIRATION_HOURS"},
            "publish_interval": {"env": "PUBLISH_INTERVAL"},
            "device_name": {"env": "DEVICE_NAME"},
            "log_level": {"env": "LOG_LEVEL"},
        }

# Global configuration instance
config = PiMonitorConfig()

def get_config() -> PiMonitorConfig:
    """Get the global configuration instance"""
    return config

def reload_config() -> PiMonitorConfig:
    """Reload configuration from environment/file"""
    global config
    config = PiMonitorConfig()
    return config

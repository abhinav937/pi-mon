#!/usr/bin/env python3
"""
Pi Monitor Configuration Loader
Simple configuration management using JSON
"""

import json
import os
from typing import Dict, Any, Optional

class Config:
    """Configuration loader for Pi Monitor"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Config file {self.config_file} not found, using defaults")
            return self._get_default_config()
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {config_file}: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration if file is missing"""
        return {
            "ports": {
                "backend": 5001,
                "frontend": 80,
                "frontend_dev": 3000
            },
            "services": {
                "backend": {
                    "name": "pi-monitor-backend",
                    "image": "pi-monitor-backend"
                },
                "frontend": {
                    "name": "pi-monitor-frontend",
                    "image": "pi-monitor-frontend"
                }
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key (supports dot notation)"""
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_port(self, service: str) -> int:
        """Get port for a specific service"""
        return self.get(f"ports.{service}", 5001)
    
    def get_service_config(self, service: str) -> Dict[str, Any]:
        """Get configuration for a specific service"""
        return self.get(f"services.{service}", {})
    
    def get_backend_endpoints(self) -> Dict[str, str]:
        """Get all backend endpoints"""
        return self.get("backend.endpoints", {})
    
    def get_urls(self, environment: str = "local") -> Dict[str, str]:
        """Get URLs for a specific environment"""
        return self.get(f"urls.{environment}", {})
    
    def reload(self):
        """Reload configuration from file"""
        self.config = self._load_config()
    
    def to_dict(self) -> Dict[str, Any]:
        """Get entire configuration as dictionary"""
        return self.config.copy()
    
    def print_summary(self):
        """Print a summary of the configuration"""
        print("Pi Monitor Configuration Summary")
        print("=" * 40)
        print(f"Project: {self.get('project.name', 'Unknown')}")
        print(f"Version: {self.get('project.version', 'Unknown')}")
        print()
        print("Ports:")
        print(f"  Backend: {self.get_port('backend')}")
        print(f"  Frontend: {self.get_port('frontend')}")
        print(f"  Frontend Dev: {self.get_port('frontend_dev')}")
        print()
        print("Services:")
        for service in ["backend", "frontend"]:
            config = self.get_service_config(service)
            print(f"  {service}: {config.get('name', 'Unknown')}")
        print()
        print("Backend Endpoints:")
        endpoints = self.get_backend_endpoints()
        for name, path in endpoints.items():
            print(f"  {name}: {path}")
        print()
        print("Local URLs:")
        urls = self.get_urls("local")
        for service, url in urls.items():
            print(f"  {service}: {url}")

# Global configuration instance
config = Config()

if __name__ == "__main__":
    # Print configuration summary when run directly
    config.print_summary()

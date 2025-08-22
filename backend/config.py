#!/usr/bin/env python3
"""
Pi Monitor - Configuration Management
Handles all configuration settings for the Pi Monitor system
"""

import json
import os
from pathlib import Path

class Config:
    """Configuration manager for Pi Monitor"""
    
    def __init__(self):
        self.config_file = self._find_config_file()
        self.config_data = self._load_config()
        self._setup_defaults()
    
    def _find_config_file(self):
        """Find the configuration file"""
        # Look for config.json in parent directory
        current_dir = Path(__file__).parent
        parent_dir = current_dir.parent
        config_path = parent_dir / "config.json"
        
        if config_path.exists():
            return str(config_path)
        
        # Fallback to local config
        return str(current_dir / "config.json")
    
    def _load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            else:
                print(f"⚠️  Config file not found: {self.config_file}")
                return {}
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            return {}
    
    def _setup_defaults(self):
        """Setup default configuration values"""
        defaults = {
            "ports": {
                "backend": 80,
                "frontend": 80,
                "frontend_dev": 3000
            },
            "backend": {
                "endpoints": {
                    "root": "/",
                    "health": "/health",
                    "auth": "/api/auth/token",
                    "system": "/api/system",
                    "metrics": "/api/metrics",
                    "system_info": "/api/system/info",
                    "services": "/api/services",
                    "power": "/api/power"
                }
            },
            "urls": {
                "production": {
                    "backend": "http://65.36.123.68:5001",
                    "frontend": "http://65.36.123.68",
                    "api_base": "http://65.36.123.68"
                }
            }
        }
        
        # Merge defaults with loaded config
        for key, value in defaults.items():
            if key not in self.config_data:
                self.config_data[key] = value
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if sub_key not in self.config_data[key]:
                        self.config_data[key][sub_key] = sub_value
    
    def get_port(self, service):
        """Get port for a specific service"""
        return self.config_data.get("ports", {}).get(service, 80)
    
    def get_backend_endpoints(self):
        """Get backend endpoints configuration"""
        return self.config_data.get("backend", {}).get("endpoints", {})
    
    def get_production_urls(self):
        """Get production URLs configuration"""
        return self.config_data.get("urls", {}).get("production", {})
    
    def get(self, key, default=None):
        """Get configuration value by key"""
        keys = key.split('.')
        value = self.config_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value

# Global configuration instance
config = Config()

if __name__ == "__main__":
    print("Pi Monitor Configuration")
    print(f"Config file: {config.config_file}")
    print(f"Backend port: {config.get_port('backend')}")
    print(f"Production API: {config.get_production_urls().get('api_base')}")

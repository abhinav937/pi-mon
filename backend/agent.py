#!/usr/bin/env python3
"""
Pi Monitor - Lightweight MQTT Agent
Publishes system metrics to MQTT broker for real-time monitoring
"""

import asyncio
import json
import os
import signal
import time
from datetime import datetime
from typing import Optional

import paho.mqtt.client as mqtt
import structlog
from dotenv import load_dotenv

from system_monitor import SystemMonitor
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

class PiMqttAgent:
    """Lightweight MQTT agent for publishing Pi system metrics"""
    
    def __init__(self):
        # Configuration (using centralized config)
        self.mqtt_broker = config.mqtt_broker
        self.mqtt_port = config.mqtt_port
        self.mqtt_username = config.mqtt_username
        self.mqtt_password = config.mqtt_password
        self.client_id = os.getenv("MQTT_CLIENT_ID", f"pi-monitor-agent-{int(time.time())}")
        self.topic_prefix = os.getenv("MQTT_TOPIC_PREFIX", "/pi")
        self.publish_interval = config.publish_interval
        self.device_name = config.device_name
        
        # MQTT client setup
        self.mqtt_client = None
        self.connected = False
        self.running = False
        
        # System monitor
        self.system_monitor = SystemMonitor()
        
        # Topics
        self.topics = {
            "cpu": f"{self.topic_prefix}/cpu",
            "memory": f"{self.topic_prefix}/memory",
            "disk": f"{self.topic_prefix}/disk",
            "temperature": f"{self.topic_prefix}/temperature",
            "network": f"{self.topic_prefix}/network",
            "uptime": f"{self.topic_prefix}/uptime",
            "status": f"{self.topic_prefix}/status"
        }
        
        # Last published values for change detection
        self._last_values = {}
        
    def _setup_mqtt_client(self):
        """Setup MQTT client with callbacks"""
        self.mqtt_client = mqtt.Client(client_id=self.client_id)
        
        # Set authentication if provided
        if self.mqtt_username and self.mqtt_password:
            self.mqtt_client.username_pw_set(self.mqtt_username, self.mqtt_password)
        
        # Setup callbacks
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_disconnect = self._on_disconnect
        self.mqtt_client.on_publish = self._on_publish
        self.mqtt_client.on_log = self._on_log
        
        # Set will message (for clean disconnection detection)
        will_payload = {
            "device": self.device_name,
            "status": "offline",
            "timestamp": datetime.utcnow().isoformat()
        }
        self.mqtt_client.will_set(
            self.topics["status"], 
            json.dumps(will_payload), 
            qos=1, 
            retain=True
        )
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for MQTT connection"""
        if rc == 0:
            self.connected = True
            logger.info("MQTT connected successfully", broker=self.mqtt_broker, client_id=self.client_id)
            
            # Publish online status
            self._publish_status("online")
        else:
            self.connected = False
            logger.error("MQTT connection failed", return_code=rc, broker=self.mqtt_broker)
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for MQTT disconnection"""
        self.connected = False
        if rc != 0:
            logger.warning("MQTT unexpected disconnection", return_code=rc)
        else:
            logger.info("MQTT disconnected cleanly")
    
    def _on_publish(self, client, userdata, mid):
        """Callback for successful publish"""
        logger.debug("MQTT message published", message_id=mid)
    
    def _on_log(self, client, userdata, level, buf):
        """Callback for MQTT client logs"""
        logger.debug("MQTT client log", level=level, message=buf)
    
    def _publish_status(self, status: str):
        """Publish device status"""
        payload = {
            "device": self.device_name,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "publish_interval": self.publish_interval,
            "topics": list(self.topics.keys())
        }
        
        self._publish_message(self.topics["status"], payload, retain=True)
    
    def _publish_message(self, topic: str, payload: dict, retain: bool = False, qos: int = 0):
        """Publish a message to MQTT broker"""
        if not self.connected:
            logger.warning("Cannot publish - MQTT not connected", topic=topic)
            return False
        
        try:
            message = json.dumps(payload)
            result = self.mqtt_client.publish(topic, message, qos=qos, retain=retain)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug("Message queued for publish", topic=topic, qos=qos, retain=retain)
                return True
            else:
                logger.error("Failed to queue message", topic=topic, return_code=result.rc)
                return False
                
        except Exception as e:
            logger.error("Error publishing message", topic=topic, error=str(e))
            return False
    
    def _should_publish_value(self, key: str, value, threshold: float = 1.0) -> bool:
        """Check if value has changed enough to warrant publishing"""
        if key not in self._last_values:
            return True
        
        last_value = self._last_values[key]
        
        # For numeric values, check threshold
        if isinstance(value, (int, float)) and isinstance(last_value, (int, float)):
            change = abs(value - last_value)
            if change >= threshold:
                return True
        # For non-numeric values, check if different
        elif value != last_value:
            return True
        
        return False
    
    async def _collect_and_publish_metrics(self):
        """Collect system metrics and publish to MQTT"""
        try:
            # Get system statistics
            stats = await self.system_monitor.get_system_stats()
            
            current_time = datetime.utcnow().isoformat()
            
            # Prepare individual metric payloads
            metrics = {
                "cpu": {
                    "device": self.device_name,
                    "value": stats.cpu_percent,
                    "unit": "percent",
                    "timestamp": current_time
                },
                "memory": {
                    "device": self.device_name,
                    "value": stats.memory_percent,
                    "unit": "percent",
                    "timestamp": current_time
                },
                "disk": {
                    "device": self.device_name,
                    "value": stats.disk_percent,
                    "unit": "percent",
                    "timestamp": current_time
                },
                "temperature": {
                    "device": self.device_name,
                    "value": stats.temperature,
                    "unit": "celsius",
                    "timestamp": current_time
                },
                "network": {
                    "device": self.device_name,
                    "bytes_sent": stats.network.get("bytes_sent", 0),
                    "bytes_recv": stats.network.get("bytes_recv", 0),
                    "packets_sent": stats.network.get("packets_sent", 0),
                    "packets_recv": stats.network.get("packets_recv", 0),
                    "bytes_sent_rate": stats.network.get("bytes_sent_rate", 0),
                    "bytes_recv_rate": stats.network.get("bytes_recv_rate", 0),
                    "timestamp": current_time
                },
                "uptime": {
                    "device": self.device_name,
                    "value": stats.uptime,
                    "timestamp": current_time
                }
            }
            
            # Publish metrics with change detection
            published_count = 0
            
            for metric_name, payload in metrics.items():
                topic = self.topics[metric_name]
                
                # Use primary value for change detection
                primary_value = payload.get("value", payload)
                
                # Check if we should publish (value changed significantly)
                if metric_name == "cpu" and self._should_publish_value(metric_name, primary_value, 2.0):
                    self._publish_message(topic, payload)
                    self._last_values[metric_name] = primary_value
                    published_count += 1
                elif metric_name == "memory" and self._should_publish_value(metric_name, primary_value, 1.0):
                    self._publish_message(topic, payload)
                    self._last_values[metric_name] = primary_value
                    published_count += 1
                elif metric_name == "disk" and self._should_publish_value(metric_name, primary_value, 0.5):
                    self._publish_message(topic, payload)
                    self._last_values[metric_name] = primary_value
                    published_count += 1
                elif metric_name == "temperature" and self._should_publish_value(metric_name, primary_value, 1.0):
                    self._publish_message(topic, payload)
                    self._last_values[metric_name] = primary_value
                    published_count += 1
                elif metric_name in ["network", "uptime"]:
                    # Always publish network and uptime
                    self._publish_message(topic, payload)
                    published_count += 1
            
            if published_count > 0:
                logger.info("Published metrics", count=published_count, topics=list(metrics.keys()))
            else:
                logger.debug("No metrics published (no significant changes)")
                
        except Exception as e:
            logger.error("Error collecting/publishing metrics", error=str(e))
    
    async def _reconnect_loop(self):
        """Handle MQTT reconnection with exponential backoff"""
        reconnect_delay = 1
        max_delay = 60
        
        while self.running and not self.connected:
            try:
                logger.info("Attempting MQTT reconnection", broker=self.mqtt_broker, delay=reconnect_delay)
                self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
                self.mqtt_client.loop_start()
                
                # Wait a bit to see if connection succeeds
                await asyncio.sleep(2)
                
                if self.connected:
                    logger.info("MQTT reconnection successful")
                    reconnect_delay = 1  # Reset delay on successful connection
                else:
                    # Exponential backoff
                    reconnect_delay = min(reconnect_delay * 2, max_delay)
                    await asyncio.sleep(reconnect_delay)
                    
            except Exception as e:
                logger.error("MQTT reconnection failed", error=str(e))
                reconnect_delay = min(reconnect_delay * 2, max_delay)
                await asyncio.sleep(reconnect_delay)
    
    async def start(self):
        """Start the MQTT agent"""
        logger.info("Starting Pi MQTT Agent", 
                   broker=self.mqtt_broker, 
                   interval=self.publish_interval,
                   device=self.device_name)
        
        self._setup_mqtt_client()
        self.running = True
        
        # Connect to MQTT broker
        try:
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
        except Exception as e:
            logger.error("Initial MQTT connection failed", error=str(e))
        
        # Main loop
        reconnect_task = None
        
        while self.running:
            try:
                # Handle reconnection if needed
                if not self.connected and (reconnect_task is None or reconnect_task.done()):
                    reconnect_task = asyncio.create_task(self._reconnect_loop())
                
                # Publish metrics if connected
                if self.connected:
                    await self._collect_and_publish_metrics()
                
                # Wait for next interval
                await asyncio.sleep(self.publish_interval)
                
            except asyncio.CancelledError:
                logger.info("MQTT agent loop cancelled")
                break
            except Exception as e:
                logger.error("Error in main loop", error=str(e))
                await asyncio.sleep(5)  # Wait before retrying
        
        # Cleanup
        await self.stop()
    
    async def stop(self):
        """Stop the MQTT agent"""
        logger.info("Stopping Pi MQTT Agent")
        self.running = False
        
        if self.connected:
            # Publish offline status
            self._publish_status("offline")
            await asyncio.sleep(1)  # Give time for message to be sent
        
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        
        logger.info("Pi MQTT Agent stopped")

# Global agent instance
agent: Optional[PiMqttAgent] = None

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal", signal=signum)
    if agent:
        asyncio.create_task(agent.stop())

# Setup signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

async def main():
    """Main function"""
    global agent
    
    try:
        agent = PiMqttAgent()
        await agent.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error("Fatal error in agent", error=str(e))
    finally:
        if agent:
            await agent.stop()

if __name__ == "__main__":
    # Run the agent
    asyncio.run(main())

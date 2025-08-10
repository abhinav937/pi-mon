#!/usr/bin/env python3
"""
Pi Monitor - Power Management Module
Handles system shutdown, restart, and power-related operations
"""

import asyncio
import os
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Optional

import structlog

logger = structlog.get_logger()

class PowerManager:
    """Power management class for system control operations"""
    
    def __init__(self):
        self.pending_actions = {}
        self._check_privileges()
    
    def _check_privileges(self):
        """Check if we have necessary privileges for power operations"""
        try:
            # Check if we can run systemctl commands
            result = subprocess.run(
                ['sudo', '-n', 'systemctl', '--version'], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            self.has_systemctl = (result.returncode == 0)
            logger.info("Power management initialized", has_systemctl=self.has_systemctl)
        except Exception as e:
            self.has_systemctl = False
            logger.warning("systemctl not available or no sudo privileges", error=str(e))
    
    async def execute_action(self, action: str, delay: int = 0) -> str:
        """
        Execute power management action
        
        Args:
            action: Either 'shutdown' or 'restart'
            delay: Delay in seconds before executing action
            
        Returns:
            Status message
        """
        if action not in ['shutdown', 'restart']:
            raise ValueError(f"Invalid action: {action}. Must be 'shutdown' or 'restart'")
        
        if delay < 0:
            delay = 0
        elif delay > 3600:  # Max 1 hour delay
            delay = 3600
        
        logger.info("Power action requested", action=action, delay=delay)
        
        if delay > 0:
            return await self._schedule_action(action, delay)
        else:
            return await self._execute_immediate_action(action)
    
    async def _schedule_action(self, action: str, delay: int) -> str:
        """Schedule a delayed power action"""
        action_id = f"{action}_{int(datetime.utcnow().timestamp())}"
        execute_time = datetime.utcnow() + timedelta(seconds=delay)
        
        self.pending_actions[action_id] = {
            "action": action,
            "scheduled_time": execute_time,
            "delay": delay
        }
        
        # Start the delayed execution task
        asyncio.create_task(self._delayed_execution(action_id, action, delay))
        
        logger.info("Power action scheduled", action=action, delay=delay, execute_time=execute_time.isoformat())
        
        return f"{action.capitalize()} scheduled in {delay} seconds at {execute_time.strftime('%H:%M:%S')}"
    
    async def _delayed_execution(self, action_id: str, action: str, delay: int):
        """Execute the power action after delay"""
        try:
            await asyncio.sleep(delay)
            
            # Check if action is still pending (not cancelled)
            if action_id in self.pending_actions:
                await self._execute_immediate_action(action)
                del self.pending_actions[action_id]
                logger.info("Scheduled power action executed", action=action, action_id=action_id)
            else:
                logger.info("Scheduled power action was cancelled", action=action, action_id=action_id)
                
        except Exception as e:
            logger.error("Error in delayed power action execution", action=action, error=str(e))
            if action_id in self.pending_actions:
                del self.pending_actions[action_id]
    
    async def _execute_immediate_action(self, action: str) -> str:
        """Execute power action immediately"""
        try:
            if action == "shutdown":
                return await self._shutdown_system()
            elif action == "restart":
                return await self._restart_system()
            else:
                raise ValueError(f"Unknown action: {action}")
                
        except Exception as e:
            logger.error("Power action failed", action=action, error=str(e))
            raise
    
    async def _shutdown_system(self) -> str:
        """Shutdown the system"""
        logger.warning("Initiating system shutdown")
        
        try:
            if self.has_systemctl:
                # Use systemctl for clean shutdown
                process = await asyncio.create_subprocess_exec(
                    'sudo', 'systemctl', 'poweroff',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    return "System shutdown initiated successfully"
                else:
                    error_msg = stderr.decode() if stderr else "Unknown error"
                    logger.error("systemctl poweroff failed", error=error_msg)
                    raise Exception(f"systemctl poweroff failed: {error_msg}")
            else:
                # Fallback to shutdown command
                process = await asyncio.create_subprocess_exec(
                    'sudo', 'shutdown', '-h', 'now',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    return "System shutdown initiated successfully"
                else:
                    error_msg = stderr.decode() if stderr else "Unknown error"
                    logger.error("shutdown command failed", error=error_msg)
                    raise Exception(f"Shutdown command failed: {error_msg}")
                    
        except Exception as e:
            logger.error("Failed to shutdown system", error=str(e))
            raise Exception(f"Shutdown failed: {str(e)}")
    
    async def _restart_system(self) -> str:
        """Restart the system"""
        logger.warning("Initiating system restart")
        
        try:
            if self.has_systemctl:
                # Use systemctl for clean restart
                process = await asyncio.create_subprocess_exec(
                    'sudo', 'systemctl', 'reboot',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    return "System restart initiated successfully"
                else:
                    error_msg = stderr.decode() if stderr else "Unknown error"
                    logger.error("systemctl reboot failed", error=error_msg)
                    raise Exception(f"systemctl reboot failed: {error_msg}")
            else:
                # Fallback to reboot command
                process = await asyncio.create_subprocess_exec(
                    'sudo', 'reboot',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    return "System restart initiated successfully"
                else:
                    error_msg = stderr.decode() if stderr else "Unknown error"
                    logger.error("reboot command failed", error=error_msg)
                    raise Exception(f"Reboot command failed: {error_msg}")
                    
        except Exception as e:
            logger.error("Failed to restart system", error=str(e))
            raise Exception(f"Restart failed: {str(e)}")
    
    async def cancel_pending_action(self, action_id: str) -> bool:
        """Cancel a pending power action"""
        if action_id in self.pending_actions:
            action_info = self.pending_actions.pop(action_id)
            logger.info("Pending power action cancelled", action_id=action_id, action=action_info.get("action"))
            return True
        return False
    
    async def get_pending_actions(self) -> Dict:
        """Get list of pending power actions"""
        current_time = datetime.utcnow()
        active_actions = {}
        
        # Clean up expired actions
        expired_actions = []
        for action_id, action_info in self.pending_actions.items():
            if current_time > action_info["scheduled_time"]:
                expired_actions.append(action_id)
            else:
                # Calculate remaining time
                remaining_seconds = (action_info["scheduled_time"] - current_time).total_seconds()
                active_actions[action_id] = {
                    **action_info,
                    "remaining_seconds": int(remaining_seconds),
                    "scheduled_time": action_info["scheduled_time"].isoformat()
                }
        
        # Remove expired actions
        for action_id in expired_actions:
            self.pending_actions.pop(action_id, None)
        
        return active_actions
    
    async def get_system_power_info(self) -> Dict:
        """Get system power-related information"""
        info = {
            "has_systemctl": self.has_systemctl,
            "pending_actions_count": len(self.pending_actions),
            "supported_actions": ["shutdown", "restart"]
        }
        
        try:
            # Try to get power supply info (if available)
            power_supply_path = "/sys/class/power_supply"
            if os.path.exists(power_supply_path):
                power_supplies = []
                for item in os.listdir(power_supply_path):
                    supply_path = os.path.join(power_supply_path, item)
                    if os.path.isdir(supply_path):
                        supply_info = {"name": item}
                        
                        # Try to read basic info
                        for prop in ["type", "status", "capacity"]:
                            prop_file = os.path.join(supply_path, prop)
                            if os.path.exists(prop_file):
                                try:
                                    with open(prop_file, 'r') as f:
                                        supply_info[prop] = f.read().strip()
                                except:
                                    pass
                        
                        power_supplies.append(supply_info)
                
                if power_supplies:
                    info["power_supplies"] = power_supplies
                    
        except Exception as e:
            logger.debug("Could not get power supply info", error=str(e))
        
        return info

# Helper functions for standalone usage
async def shutdown_system(delay: int = 0) -> str:
    """Helper function to shutdown system"""
    power_manager = PowerManager()
    return await power_manager.execute_action("shutdown", delay)

async def restart_system(delay: int = 0) -> str:
    """Helper function to restart system"""
    power_manager = PowerManager()
    return await power_manager.execute_action("restart", delay)

if __name__ == "__main__":
    # Test the power manager
    async def test():
        power_manager = PowerManager()
        
        # Get system power info
        info = await power_manager.get_system_power_info()
        print(f"Power Info: {info}")
        
        # Test scheduling (but don't actually execute)
        print("Testing power action scheduling...")
        # result = await power_manager.execute_action("shutdown", 10)
        # print(f"Schedule result: {result}")
        
        # pending = await power_manager.get_pending_actions()
        # print(f"Pending actions: {pending}")
    
    asyncio.run(test())

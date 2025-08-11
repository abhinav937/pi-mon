#!/usr/bin/env python3
"""
Pi Monitor - Service Management Module
Handles system service control and monitoring
"""

import asyncio
import platform
import re
import subprocess
from typing import Dict, List, Optional

import structlog

logger = structlog.get_logger()

class ServiceManager:
    """Service management class for controlling system services"""
    
    def __init__(self):
        self.os_type = platform.system().lower()
        self.is_windows = self.os_type == 'windows'
        self.is_linux = self.os_type == 'linux'
        self._check_privileges()
        
        # Services to monitor based on OS
        if self.is_windows:
            self.default_services = [
                "Spooler", "Themes", "AudioSrv", "BITS", "Browser", 
                "Dhcp", "Dnscache", "EventLog", "LanmanServer", "Netlogon"
            ]
        else:
            # Common services to monitor on Raspberry Pi/Linux
            self.default_services = [
                "ssh", "nginx", "apache2", "mosquitto", "redis-server",
                "docker", "pi-monitor", "bluetooth", "wifi", "dhcpcd"
            ]
    
    def _check_privileges(self):
        """Check if we have necessary privileges for service operations"""
        if self.is_windows:
            # Windows uses sc command for service management
            try:
                result = subprocess.run(
                    ['sc', 'query', 'state=all'], 
                    capture_output=True, 
                    text=True, 
                    timeout=5
                )
                self.has_systemctl = False
                self.has_service_commands = (result.returncode == 0)
                logger.info("Service management initialized for Windows", has_service_commands=self.has_service_commands)
            except Exception as e:
                self.has_systemctl = False
                self.has_service_commands = False
                logger.warning("Windows service commands not available", error=str(e))
        else:
            # Linux uses systemctl
            try:
                result = subprocess.run(
                    ['sudo', '-n', 'systemctl', '--version'], 
                    capture_output=True, 
                    text=True, 
                    timeout=5
                )
                self.has_systemctl = (result.returncode == 0)
                self.has_service_commands = self.has_systemctl
                logger.info("Service management initialized for Linux", has_systemctl=self.has_systemctl)
            except Exception as e:
                self.has_systemctl = False
                self.has_service_commands = False
                logger.warning("systemctl not available or no sudo privileges", error=str(e))
    
    async def get_service_status(self, service_name: str) -> Dict:
        """Get detailed status of a specific service"""
        try:
            if not self.has_service_commands:
                return {
                    "name": service_name,
                    "status": "unknown",
                    "active": False,
                    "enabled": False,
                    "description": f"Service management not available on {self.os_type}",
                    "error": f"Service commands not available on {self.os_type}"
                }
            
            if self.is_windows:
                return await self._get_windows_service_status(service_name)
            else:
                return await self._get_linux_service_status(service_name)
                
        except Exception as e:
            logger.error("Error getting service status", service=service_name, error=str(e))
            return {
                "name": service_name,
                "status": "error",
                "error": str(e)
            }
    
    async def _get_linux_service_status(self, service_name: str) -> Dict:
        """Get service status on Linux using systemctl"""
        # Run systemctl status command
        process = await asyncio.create_subprocess_exec(
            'systemctl', 'status', service_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        output = stdout.decode()
        
        # Parse systemctl output
        service_info = {
            "name": service_name,
            "status": "unknown",
            "active": False,
            "enabled": False,
            "description": "",
            "main_pid": None,
            "memory_usage": None,
            "cpu_usage": None
        }
        
        # Parse status from output
        if "Active: active (running)" in output:
            service_info["status"] = "running"
            service_info["active"] = True
        elif "Active: inactive (dead)" in output:
            service_info["status"] = "stopped"
            service_info["active"] = False
        elif "Active: failed" in output:
            service_info["status"] = "failed"
            service_info["active"] = False
        elif "could not be found" in output or process.returncode == 4:
            service_info["status"] = "not_found"
            return service_info
        
        # Parse description
        desc_match = re.search(r'Description:\s*(.+)', output)
        if desc_match:
            service_info["description"] = desc_match.group(1).strip()
        
        # Parse main PID
        pid_match = re.search(r'Main PID:\s*(\d+)', output)
        if pid_match:
            service_info["main_pid"] = int(pid_match.group(1))
        
        # Check if service is enabled
        try:
            enabled_process = await asyncio.create_subprocess_exec(
                'systemctl', 'is-enabled', service_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            enabled_stdout, _ = await enabled_process.communicate()
            enabled_output = enabled_stdout.decode().strip()
            service_info["enabled"] = (enabled_output == "enabled")
        except Exception as e:
            logger.debug("Could not check if service is enabled", service=service_name, error=str(e))
        
        logger.debug("Service status retrieved", service=service_name, status=service_info["status"])
        return service_info
    
    async def _get_windows_service_status(self, service_name: str) -> Dict:
        """Get service status on Windows using sc command"""
        try:
            # Query service status
            process = await asyncio.create_subprocess_exec(
                'sc', 'query', service_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            output = stdout.decode()
            
            service_info = {
                "name": service_name,
                "status": "unknown",
                "active": False,
                "enabled": False,
                "description": f"Windows service: {service_name}",
                "main_pid": None
            }
            
            if process.returncode == 0:
                # Parse Windows service output
                if "STATE" in output:
                    if "RUNNING" in output:
                        service_info["status"] = "running"
                        service_info["active"] = True
                    elif "STOPPED" in output:
                        service_info["status"] = "stopped"
                        service_info["active"] = False
                    elif "START_PENDING" in output:
                        service_info["status"] = "starting"
                        service_info["active"] = False
                    elif "STOP_PENDING" in output:
                        service_info["status"] = "stopping"
                        service_info["active"] = True
                        
                # Try to get service configuration for startup type
                try:
                    config_process = await asyncio.create_subprocess_exec(
                        'sc', 'qc', service_name,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    config_stdout, _ = await config_process.communicate()
                    config_output = config_stdout.decode()
                    
                    if "AUTO_START" in config_output or "DELAYED_AUTO_START" in config_output:
                        service_info["enabled"] = True
                        
                except Exception as e:
                    logger.debug("Could not get service config", service=service_name, error=str(e))
            else:
                if "1060" in stderr.decode():  # Service does not exist
                    service_info["status"] = "not_found"
                else:
                    service_info["status"] = "error"
                    service_info["error"] = stderr.decode()
            
            return service_info
            
        except Exception as e:
            logger.error("Error getting Windows service status", service=service_name, error=str(e))
            return {
                "name": service_name,
                "status": "error", 
                "error": str(e)
            }
    
    async def get_services_status(self, services: Optional[List[str]] = None) -> List[Dict]:
        """Get status of multiple services"""
        if services is None:
            services = self.default_services
        
        # Get all service statuses concurrently
        tasks = [self.get_service_status(service) for service in services]
        service_statuses = await asyncio.gather(*tasks)
        
        # Filter out services that don't exist
        active_services = [
            status for status in service_statuses 
            if status.get("status") != "not_found"
        ]
        
        logger.info("Retrieved status for services", count=len(active_services))
        return active_services
    
    async def execute_action(self, service_name: str, action: str) -> str:
        """
        Execute action on a service
        
        Args:
            service_name: Name of the service
            action: One of 'start', 'stop', 'restart', 'reload', 'enable', 'disable', 'status'
            
        Returns:
            Result message
        """
        valid_actions = ['start', 'stop', 'restart', 'reload', 'enable', 'disable', 'status']
        if action not in valid_actions:
            raise ValueError(f"Invalid action: {action}. Must be one of {valid_actions}")
        
        logger.info("Service action requested", service=service_name, action=action, os_type=self.os_type)
        
        # Handle status action separately
        if action == 'status':
            status = await self.get_service_status(service_name)
            return f"Service {service_name}: {status.get('status', 'unknown')}"
        
        # Check if service commands are available
        if not self.has_service_commands:
            logger.warning("Service commands not available", os_type=self.os_type)
            return f"[SIMULATION] Service {service_name} {action} would be executed (not available on {self.os_type})"
        
        try:
            if self.is_windows:
                return await self._execute_windows_service_action(service_name, action)
            else:
                return await self._execute_linux_service_action(service_name, action)
                
        except Exception as e:
            logger.error("Service action error", service=service_name, action=action, error=str(e))
            raise Exception(f"Failed to {action} service {service_name}: {str(e)}")
    
    async def _execute_linux_service_action(self, service_name: str, action: str) -> str:
        """Execute service action on Linux using systemctl"""
        # Execute the systemctl command
        cmd_parts = ['sudo', 'systemctl', action, service_name]
        
        process = await asyncio.create_subprocess_exec(
            *cmd_parts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            logger.info("Service action completed successfully", service=service_name, action=action)
            return f"Service {service_name} {action} completed successfully"
        else:
            error_msg = stderr.decode() if stderr else stdout.decode()
            logger.error("Service action failed", service=service_name, action=action, error=error_msg)
            raise Exception(f"Service {action} failed: {error_msg}")
    
    async def _execute_windows_service_action(self, service_name: str, action: str) -> str:
        """Execute service action on Windows using sc command"""
        # Map actions to Windows sc commands
        action_map = {
            'start': 'start',
            'stop': 'stop',
            'restart': 'stop',  # Windows doesn't have restart, need to stop then start
            'enable': 'config',
            'disable': 'config'
        }
        
        if action not in action_map:
            return f"[SIMULATION] Action {action} not supported on Windows for service {service_name}"
        
        if action == 'restart':
            # For restart, stop first then start
            try:
                # Stop the service
                stop_process = await asyncio.create_subprocess_exec(
                    'sc', 'stop', service_name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await stop_process.communicate()
                
                # Wait a moment
                await asyncio.sleep(2)
                
                # Start the service
                start_process = await asyncio.create_subprocess_exec(
                    'sc', 'start', service_name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await start_process.communicate()
                
                if start_process.returncode == 0:
                    return f"Service {service_name} restarted successfully"
                else:
                    error_msg = stderr.decode() if stderr else "Unknown error"
                    raise Exception(f"Service restart failed: {error_msg}")
                    
            except Exception as e:
                logger.error("Windows service restart failed", service=service_name, error=str(e))
                raise
        
        elif action in ['enable', 'disable']:
            # For enable/disable, modify service startup type
            startup_type = 'auto' if action == 'enable' else 'disabled'
            process = await asyncio.create_subprocess_exec(
                'sc', 'config', service_name, f'start={startup_type}',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return f"Service {service_name} {action}d successfully"
            else:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise Exception(f"Service {action} failed: {error_msg}")
        
        else:
            # For start/stop
            process = await asyncio.create_subprocess_exec(
                'sc', action_map[action], service_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return f"Service {service_name} {action} completed successfully"
            else:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise Exception(f"Service {action} failed: {error_msg}")
    
    async def get_failed_services(self) -> List[Dict]:
        """Get list of failed services"""
        try:
            if not self.has_systemctl:
                return []
            
            process = await asyncio.create_subprocess_exec(
                'systemctl', '--failed', '--no-legend',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.warning("Could not get failed services", error=stderr.decode())
                return []
            
            failed_services = []
            output_lines = stdout.decode().strip().split('\n')
            
            for line in output_lines:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 1:
                        service_name = parts[0].replace('.service', '')
                        # Get detailed status for failed service
                        status = await self.get_service_status(service_name)
                        failed_services.append(status)
            
            logger.info("Retrieved failed services", count=len(failed_services))
            return failed_services
            
        except Exception as e:
            logger.error("Error getting failed services", error=str(e))
            return []
    
    async def get_system_services_overview(self) -> Dict:
        """Get overview of system services"""
        try:
            overview = {
                "total_services": 0,
                "running_services": 0,
                "failed_services": 0,
                "stopped_services": 0,
                "has_systemctl": self.has_systemctl
            }
            
            if not self.has_systemctl:
                return overview
            
            # Get count of all services
            process = await asyncio.create_subprocess_exec(
                'systemctl', 'list-units', '--type=service', '--no-legend', '--no-pager',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                lines = stdout.decode().strip().split('\n')
                total_services = len([line for line in lines if line.strip()])
                overview["total_services"] = total_services
                
                # Count running services
                running_count = len([line for line in lines if 'running' in line])
                overview["running_services"] = running_count
                
                # Count failed services
                failed_count = len([line for line in lines if 'failed' in line])
                overview["failed_services"] = failed_count
                
                # Calculate stopped services
                overview["stopped_services"] = total_services - running_count - failed_count
            
            return overview
            
        except Exception as e:
            logger.error("Error getting services overview", error=str(e))
            return {
                "error": str(e),
                "has_systemctl": self.has_systemctl
            }
    
    async def search_services(self, pattern: str) -> List[str]:
        """Search for services matching a pattern"""
        try:
            if not self.has_systemctl:
                return []
            
            process = await asyncio.create_subprocess_exec(
                'systemctl', 'list-units', '--type=service', '--no-legend', '--no-pager',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                return []
            
            matching_services = []
            lines = stdout.decode().strip().split('\n')
            
            for line in lines:
                if line.strip():
                    service_name = line.split()[0].replace('.service', '')
                    if pattern.lower() in service_name.lower():
                        matching_services.append(service_name)
            
            logger.info("Service search completed", pattern=pattern, matches=len(matching_services))
            return matching_services[:20]  # Limit to 20 results
            
        except Exception as e:
            logger.error("Error searching services", pattern=pattern, error=str(e))
            return []

# Helper functions for standalone usage
async def get_service_info(service_name: str) -> Dict:
    """Helper function to get service information"""
    service_manager = ServiceManager()
    return await service_manager.get_service_status(service_name)

async def control_service(service_name: str, action: str) -> str:
    """Helper function to control a service"""
    service_manager = ServiceManager()
    return await service_manager.execute_action(service_name, action)

if __name__ == "__main__":
    # Test the service manager
    async def test():
        service_manager = ServiceManager()
        
        # Get services overview
        overview = await service_manager.get_system_services_overview()
        print(f"Services Overview: {overview}")
        
        # Get status of common services
        services = await service_manager.get_services_status(['ssh', 'nginx'])
        print(f"Service Statuses: {services}")
        
        # Get failed services
        failed = await service_manager.get_failed_services()
        print(f"Failed Services: {failed}")
        
        # Search for services
        search_results = await service_manager.search_services("ssh")
        print(f"SSH Services: {search_results}")
    
    asyncio.run(test())

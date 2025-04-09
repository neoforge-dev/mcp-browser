import pytest
import docker
import subprocess
import socket
import time
from typing import Dict, List
import asyncio
import logging
import uuid
from src.browser_pool import BrowserPool, BrowserInstance
from src.error_handler import MCPBrowserException, ErrorCode
from playwright.async_api import Route, Request
import json

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more verbose output
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test-network-isolation")

@pytest.fixture(scope="module")
def docker_client():
    try:
        client = docker.from_env()
        return client
    except docker.errors.DockerException as e:
        logger.error(f"Failed to connect to Docker: {e}")
        pytest.skip("Docker is not available")

@pytest.fixture(scope="module")
def mcp_browser_container(docker_client):
    """Get the MCP Browser container"""
    containers = docker_client.containers.list(filters={"name": "mcp-browser"})
    assert len(containers) == 1, "MCP Browser container not found"
    return containers[0]

def test_network_configuration(docker_client):
    """Test Docker network configuration"""
    networks = docker_client.networks.list()
    
    # Check required networks exist
    network_names = [n.name for n in networks]
    assert "mcp-browser-internal" in network_names
    assert "mcp-browser-external" in network_names
    assert "mcp-browser-monitoring" in network_names
    
    # Verify network configurations
    for network in networks:
        if network.name.startswith("mcp-browser-"):
            config = network.attrs["IPAM"]["Config"][0]
            assert "Subnet" in config
            assert "Gateway" in config
            assert network.attrs["Driver"] == "bridge"

def test_container_network_access(mcp_browser_container):
    """Test container network access restrictions"""
    # Test internal network access
    internal_ip = "172.20.0.1"
    result = mcp_browser_container.exec_run(f"ping -c 1 {internal_ip}")
    assert result.exit_code != 0, "Container should not be able to ping internal network"
    
    # Test external network access
    external_ip = "172.21.0.1"
    result = mcp_browser_container.exec_run(f"ping -c 1 {external_ip}")
    assert result.exit_code != 0, "Container should not be able to ping external network"
    
    # Test monitoring network access
    monitoring_ip = "172.22.0.1"
    result = mcp_browser_container.exec_run(f"ping -c 1 {monitoring_ip}")
    assert result.exit_code != 0, "Container should not be able to ping monitoring network"

def test_port_access(mcp_browser_container):
    """Test port access restrictions"""
    # Test allowed ports
    allowed_ports = [8000, 7665]
    for port in allowed_ports:
        result = mcp_browser_container.exec_run(f"nc -zv localhost {port}")
        assert result.exit_code == 0, f"Container should be able to access port {port}"
    
    # Test blocked ports
    blocked_ports = [22, 80, 443]
    for port in blocked_ports:
        result = mcp_browser_container.exec_run(f"nc -zv localhost {port}")
        assert result.exit_code != 0, f"Container should not be able to access port {port}"

def test_apparmor_profile(mcp_browser_container):
    """Test AppArmor profile enforcement"""
    # Check if AppArmor profile is loaded
    result = subprocess.run(["aa-status"], capture_output=True, text=True)
    assert "mcp-browser" in result.stdout, "AppArmor profile not loaded"
    
    # Test raw socket access (should be denied)
    result = mcp_browser_container.exec_run("python3 -c 'import socket; s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)'")
    assert result.exit_code != 0, "Container should not be able to create raw sockets"

def test_tcp_hardening(mcp_browser_container):
    """Test TCP hardening settings"""
    # Get container's TCP settings
    result = mcp_browser_container.exec_run("cat /proc/sys/net/ipv4/tcp_syncookies")
    assert result.exit_code == 0
    assert result.output.decode().strip() == "1", "TCP syncookies should be enabled"
    
    result = mcp_browser_container.exec_run("cat /proc/sys/net/ipv4/tcp_max_syn_backlog")
    assert result.exit_code == 0
    assert result.output.decode().strip() == "1024", "TCP max syn backlog should be 1024"
    
    result = mcp_browser_container.exec_run("cat /proc/sys/net/ipv4/tcp_synack_retries")
    assert result.exit_code == 0
    assert result.output.decode().strip() == "2", "TCP synack retries should be 2"

def test_resource_limits(mcp_browser_container):
    """Test resource limits"""
    # Get container's resource limits
    result = mcp_browser_container.exec_run("ulimit -n")
    assert result.exit_code == 0
    assert int(result.output.decode().strip()) == 65536, "File descriptor limit should be 65536"
    
    result = mcp_browser_container.exec_run("ulimit -u")
    assert result.exit_code == 0
    assert int(result.output.decode().strip()) == 65536, "Process limit should be 65536"

@pytest.mark.timeout(60)  # Increase timeout to 60 seconds
@pytest.mark.asyncio
async def test_network_isolation():
    """Test that network isolation is properly enforced."""
    logger.debug("Starting network isolation test")
    
    async def mock_response(route: Route, request: Request):
        if "example.com" in request.url:
            await route.fulfill(status=200, body="Example.com response")
        elif "blocked.com" in request.url:
            await route.abort()
        else:
            await route.abort()
    
    pool = None
    browser = None
    context = None
    context_id = str(uuid.uuid4())
    
    try:
        # Initialize browser pool with network isolation
        pool = BrowserPool(
            max_browsers=1,
            idle_timeout=60,
            max_memory_percent=80,
            max_cpu_percent=80,
            network_isolation=True,
            allowed_domains=["example.com"],
            blocked_domains=["blocked.com"]
        )
        
        logger.debug("Getting browser instance...")
        browser = await asyncio.wait_for(pool.get_browser(), timeout=10.0)
        assert browser is not None, "Failed to get browser instance"
        assert browser.network_isolation, "Network isolation should be enabled"
        
        logger.debug(f"Creating browser context with ID {context_id}...")
        context = await asyncio.wait_for(browser.create_context(context_id), timeout=10.0)
        assert context is not None, "Failed to create browser context"
        
        # Test access to allowed domain
        logger.debug("Testing access to allowed domain (example.com)")
        page = await asyncio.wait_for(context.new_page(), timeout=10.0)
        try:
            # Route all network requests through our mock
            await asyncio.wait_for(page.route("**/*", mock_response), timeout=5.0)
            
            response = await asyncio.wait_for(
                page.goto("http://example.com", wait_until="networkidle"),
                timeout=5.0
            )
            assert response is not None, "Failed to access allowed domain"
            assert response.status == 200, "Failed to get successful response from allowed domain"
            logger.debug("Successfully accessed allowed domain")
        finally:
            await asyncio.wait_for(page.close(), timeout=5.0)
        
        # Test access to blocked domain
        logger.debug("Testing access to blocked domain (blocked.com)")
        page = await asyncio.wait_for(context.new_page(), timeout=10.0)
        try:
            await asyncio.wait_for(page.route("**/*", mock_response), timeout=5.0)
            
            with pytest.raises(Exception) as exc_info:
                await asyncio.wait_for(
                    page.goto("http://blocked.com", wait_until="networkidle"),
                    timeout=5.0
                )
            error_msg = str(exc_info.value).lower()
            assert any(msg in error_msg for msg in ["blocked", "err_failed"]), \
                   f"Expected blocked domain to be blocked, got error: {error_msg}"
            logger.debug("Successfully blocked access to blocked domain")
        finally:
            await asyncio.wait_for(page.close(), timeout=5.0)
        
        # Test access to unlisted domain
        logger.debug("Testing access to unlisted domain (unlisted.com)")
        page = await asyncio.wait_for(context.new_page(), timeout=10.0)
        try:
            await asyncio.wait_for(page.route("**/*", mock_response), timeout=5.0)
            
            with pytest.raises(Exception) as exc_info:
                await asyncio.wait_for(
                    page.goto("http://unlisted.com", wait_until="networkidle"),
                    timeout=5.0
                )
            error_msg = str(exc_info.value).lower()
            assert any(msg in error_msg for msg in ["not allowed", "err_failed"]), \
                   f"Expected unlisted domain to be blocked, got error: {error_msg}"
            logger.debug("Successfully blocked access to unlisted domain")
        finally:
            await asyncio.wait_for(page.close(), timeout=5.0)
        
    except Exception as e:
        logger.error(f"Error in network isolation test: {str(e)}", exc_info=True)
        raise
    
    finally:
        # Clean up resources in reverse order
        try:
            if context and browser:
                logger.debug(f"Closing browser context {context_id}...")
                await asyncio.wait_for(browser.close_context(context_id), timeout=5.0)
            
            if browser and pool:
                logger.debug("Returning browser to pool...")
                await asyncio.wait_for(pool.close_browser(browser), timeout=5.0)
            
            if pool:
                logger.debug("Cleaning up browser pool...")
                await asyncio.wait_for(pool.cleanup(), timeout=5.0)
        except asyncio.TimeoutError as te:
            logger.error(f"Timeout during cleanup: {str(te)}")
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup: {str(cleanup_error)}", exc_info=True)
        
        logger.debug("Network isolation test completed")

if __name__ == "__main__":
    asyncio.run(test_network_isolation()) 
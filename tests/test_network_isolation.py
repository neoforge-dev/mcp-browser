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
from playwright.async_api import Route, Request, Page, Error as PlaywrightError
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO, # Use INFO for less noise
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test-network-isolation")

def test_network_configuration(docker_client):
    """Test Docker network configuration"""
    networks = docker_client.networks.list()
    network_names = [n.name for n in networks]
    assert "mcp-browser-internal" in network_names
    assert "mcp-browser-external" in network_names
    assert "mcp-browser-monitoring" in network_names
    for network in networks:
        if network.name.startswith("mcp-browser-"):
            config = network.attrs["IPAM"]["Config"][0]
            assert "Subnet" in config
            assert "Gateway" in config
            assert network.attrs["Driver"] == "bridge"

def test_container_network_access(mcp_browser_container):
    """Test container network access restrictions"""
    internal_ip = "172.20.0.1"
    result = mcp_browser_container.exec_run(f"ping -c 1 {internal_ip}")
    assert result.exit_code != 0
    external_ip = "172.21.0.1"
    result = mcp_browser_container.exec_run(f"ping -c 1 {external_ip}")
    assert result.exit_code != 0
    monitoring_ip = "172.22.0.1"
    result = mcp_browser_container.exec_run(f"ping -c 1 {monitoring_ip}")
    assert result.exit_code != 0

def test_port_access(mcp_browser_container):
    """Test port access restrictions. Only check allowed exposed ports."""
    # Only check port 7665, which is explicitly exposed and used by healthcheck
    allowed_ports = [7665] 
    for port in allowed_ports:
        # Adding a small delay to allow the service potentially listening on 7665 to start
        time.sleep(1) 
        result = mcp_browser_container.exec_run(f"nc -zv localhost {port}")
        # If the healthcheck uses this port, it should succeed.
        # If nc returns 0, the port is open.
        assert result.exit_code == 0, f"Port {port} should be accessible, nc exited with {result.exit_code}. Output: {result.output.decode()}"

    blocked_ports = [22, 80, 443, 8000] # Add 8000 to blocked as main app shouldn't run
    for port in blocked_ports:
        result = mcp_browser_container.exec_run(f"nc -zv localhost {port}")
        # If nc returns non-0, the port is closed or filtered.
        assert result.exit_code != 0, f"Port {port} should NOT be accessible, nc exited with {result.exit_code}. Output: {result.output.decode()}"

def test_apparmor_profile(mcp_browser_container):
    """Test AppArmor profile enforcement"""
    # Check if AppArmor profile is loaded for the container
    # Run aa-status inside the container
    aa_status_result = mcp_browser_container.exec_run("aa-status")
    assert aa_status_result.exit_code == 0, f"aa-status failed: {aa_status_result.output.decode()}"
    assert "mcp-browser" in aa_status_result.output.decode(), "mcp-browser AppArmor profile not found in aa-status output"
    
    # Test if raw socket creation is restricted
    raw_socket_result = mcp_browser_container.exec_run("python3 -c 'import socket; s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)'")
    assert raw_socket_result.exit_code != 0, "Raw socket creation should be blocked by AppArmor"

def test_tcp_hardening(mcp_browser_container):
    """Test TCP hardening settings"""
    result = mcp_browser_container.exec_run("cat /proc/sys/net/ipv4/tcp_syncookies")
    assert result.exit_code == 0 and result.output.decode().strip() == "1"
    result = mcp_browser_container.exec_run("cat /proc/sys/net/ipv4/tcp_max_syn_backlog")
    assert result.exit_code == 0 and result.output.decode().strip() == "1024"
    result = mcp_browser_container.exec_run("cat /proc/sys/net/ipv4/tcp_synack_retries")
    assert result.exit_code == 0 and result.output.decode().strip() == "2"

def test_resource_limits(mcp_browser_container):
    """Test resource limits"""
    result = mcp_browser_container.exec_run("ulimit -n")
    assert result.exit_code == 0 and int(result.output.decode().strip()) == 65536
    result = mcp_browser_container.exec_run("ulimit -u")
    assert result.exit_code == 0 and int(result.output.decode().strip()) == 65536

async def _safe_goto(page: Page, url: str, timeout: float = 25.0):
    """Helper function to navigate and handle potential errors."""
    logger.debug(f"_safe_goto: Attempting navigation to {url} with timeout {timeout}s")
    start_time = asyncio.get_event_loop().time()
    try:
        response = await asyncio.wait_for(
            page.goto(url, wait_until="domcontentloaded"), # Using domcontentloaded for faster feedback
            timeout=timeout
        )
        end_time = asyncio.get_event_loop().time()
        logger.debug(f"_safe_goto: Navigation to {url} successful in {end_time - start_time:.2f}s. Status: {response.status if response else 'N/A'}")
        return response, None
    except asyncio.TimeoutError as e:
        end_time = asyncio.get_event_loop().time()
        logger.error(f"_safe_goto: Navigation to {url} timed out after {end_time - start_time:.2f}s")
        return None, e
    except PlaywrightError as e:
        end_time = asyncio.get_event_loop().time()
        logger.error(f"_safe_goto: PlaywrightError during navigation to {url} after {end_time - start_time:.2f}s: {type(e).__name__} - {str(e)}")
        return None, e
    except Exception as e:
        # Catch any other unexpected errors during goto
        end_time = asyncio.get_event_loop().time()
        logger.error(f"_safe_goto: Unexpected exception during navigation to {url} after {end_time - start_time:.2f}s: {type(e).__name__} - {str(e)}", exc_info=True)
        return None, e

@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_allowed_domain_access(browser_context):
    """Test access to a domain allowed by the pool configuration."""
    # --- Connectivity Check Removed ---
    domain = "example.com"

    page = await browser_context.new_page()
    logger.info(f"Testing access to allowed domain: {domain}")
    response, error = await _safe_goto(page, f"http://{domain}")
    assert error is None, f"Navigation to allowed domain {domain} failed: {error}"
    assert response is not None and response.ok, f"Failed to get successful response from allowed domain {domain}"
    logger.info("Successfully accessed allowed domain.")
    await page.close()

@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_blocked_domain_access(browser_context):
    """Test access to a domain explicitly blocked by the pool configuration."""
    page = await browser_context.new_page()
    logger.info("Testing access to blocked domain: blocked.com")
    response, error = await _safe_goto(page, "http://blocked.com")
    assert error is not None, "Navigation to blocked domain blocked.com should have failed"
    assert response is None or not response.ok, "Response from blocked domain blocked.com should not be OK"
    # Check error message for indication of blocking
    error_msg = str(error).lower()
    assert "net::err_failed" in error_msg or "blocked" in error_msg, \
           f"Expected network error for blocked domain, got: {error_msg}"
    logger.info("Successfully blocked access to blocked domain.")
    await page.close()

@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_unlisted_domain_access(browser_context):
    """Test access to a domain not listed in allowed/blocked (should be blocked)."""
    page = await browser_context.new_page()
    logger.info("Testing access to unlisted domain: unlisted-random.org")
    # Use a domain unlikely to exist to ensure it's truly unlisted
    response, error = await _safe_goto(page, "http://unlisted-random.org") 
    assert error is not None, "Navigation to unlisted domain unlisted-random.org should have failed"
    assert response is None or not response.ok, "Response from unlisted domain unlisted-random.org should not be OK"
    # Check error message for indication of blocking
    error_msg = str(error).lower()
    assert "net::err_failed" in error_msg or "blocked" in error_msg or "not allowed" in error_msg, \
           f"Expected network error for unlisted domain, got: {error_msg}"
    logger.info("Successfully blocked access to unlisted domain.")
    await page.close()

if __name__ == "__main__":
    asyncio.run(test_network_isolation()) 
#!/bin/bash
set -e

# Create Docker networks if they don't exist
docker network create mcp-browser-internal || true
docker network create mcp-browser-external || true
docker network create mcp-browser-monitoring || true

# Configure iptables rules
iptables -N MCP_BROWSER_FORWARD
iptables -A FORWARD -j MCP_BROWSER_FORWARD

# Allow established connections
iptables -A MCP_BROWSER_FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow internal network communication
iptables -A MCP_BROWSER_FORWARD -s 172.20.0.0/16 -d 172.20.0.0/16 -j ACCEPT

# Allow monitoring network to internal network
iptables -A MCP_BROWSER_FORWARD -s 172.22.0.0/16 -d 172.20.0.0/16 -j ACCEPT

# Allow external network to specific ports
iptables -A MCP_BROWSER_FORWARD -s 172.21.0.0/16 -d 172.20.0.0/16 -p tcp --dport 8000 -j ACCEPT
iptables -A MCP_BROWSER_FORWARD -s 172.21.0.0/16 -d 172.20.0.0/16 -p tcp --dport 7665 -j ACCEPT

# Drop all other traffic
iptables -A MCP_BROWSER_FORWARD -j DROP

# Enable IP forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward

# Configure TCP hardening
echo 1 > /proc/sys/net/ipv4/tcp_syncookies
echo 1024 > /proc/sys/net/ipv4/tcp_max_syn_backlog
echo 2 > /proc/sys/net/ipv4/tcp_synack_retries

# Save iptables rules
iptables-save > /etc/iptables/rules.v4

echo "Network isolation and firewall rules configured successfully." 
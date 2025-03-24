#!/bin/bash
#
# MCP Browser Installer
# This script installs and configures MCP Browser for visual testing on Mac

set -e

# Configuration variables
REPO_URL="https://github.com/neoforge-dev/mcp-browser.git"
INSTALL_DIR="$HOME/mcp-browser"
PORT=7665
SECRET=$(openssl rand -hex 16)
LOG_FILE="$HOME/mcp-browser-install.log"

# Show banner
echo "========================================"
echo "      MCP Browser Installer"
echo "========================================"
echo ""
echo "This will install MCP Browser on your Mac"
echo "with visualization support for AI agents."
echo ""

# Ask for confirmation
read -p "Continue with installation? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Installation cancelled."
  exit 0
fi

# Function to check for prerequisites
check_prerequisites() {
  echo "Checking prerequisites..."
  
  # Check for Git
  if ! command -v git &> /dev/null; then
    echo "Git not found. Installing..."
    brew install git
  fi
  
  # Check for Docker
  if ! command -v docker &> /dev/null; then
    echo "Docker not found. Installing..."
    brew install docker
    brew install docker-compose
  fi
  
  # Check for Python
  if ! command -v python3 &> /dev/null; then
    echo "Python not found. Installing..."
    brew install python
  fi
  
  # Check for XQuartz (X11 for Mac)
  if ! command -v xquartz &> /dev/null; then
    echo "XQuartz not found. Installing..."
    brew install --cask xquartz
  fi
}

# Function to clone or update repository
setup_repository() {
  echo "Setting up repository..."
  
  if [ -d "$INSTALL_DIR" ]; then
    echo "Repository exists. Updating..."
    cd "$INSTALL_DIR"
    git pull
  else
    echo "Cloning repository..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
  fi
}

# Function to configure environment
configure_environment() {
  echo "Configuring environment..."
  
  # Create .env file
  cat > "$INSTALL_DIR/.env" << EOF
MCP_SECRET=$SECRET
SERVER_PORT=8000
EOF

  # Create browser display configuration
  echo "Configuring browser display..."
  mkdir -p "$HOME/.mcp-browser"
  cat > "$HOME/.mcp-browser/config.json" << EOF
{
  "display": {
    "width": 1280,
    "height": 800,
    "deviceScaleFactor": 2,
    "mobile": false
  },
  "server": {
    "port": $PORT,
    "secret": "$SECRET"
  },
  "browser": {
    "headless": false,
    "defaultViewport": null
  }
}
EOF
}

# Function to start services
start_services() {
  echo "Starting services..."
  
  # Start XQuartz if not running
  if ! pgrep -x "Xquartz" > /dev/null && ! pgrep -x "X11" > /dev/null; then
    echo "Starting XQuartz X11 server..."
    # Try running the binary directly
    if [ -f "/Applications/Utilities/XQuartz.app/Contents/MacOS/X11" ]; then
      echo "Using XQuartz binary directly..."
      /Applications/Utilities/XQuartz.app/Contents/MacOS/X11 &
      sleep 5
    elif [ -f "/opt/X11/bin/Xquartz" ]; then
      echo "Using Xquartz binary from /opt/X11/bin..."
      /opt/X11/bin/Xquartz &
      sleep 5
    else
      echo "Trying to open XQuartz application..."
      open "/Applications/Utilities/XQuartz.app"
      sleep 5
      
      # Check if XQuartz started successfully
      if ! pgrep -x "Xquartz" > /dev/null && ! pgrep -x "X11" > /dev/null; then
        echo "WARNING: Could not start XQuartz automatically."
        echo "You may need to start it manually before proceeding."
        echo "Try running: /Applications/Utilities/XQuartz.app/Contents/MacOS/X11"
        echo "Or open XQuartz from your Applications folder."
        read -p "Press Enter to continue once XQuartz is running, or Ctrl+C to abort..."
      fi
    fi
  else
    echo "XQuartz is already running."
  fi
  
  # Start MCP Browser
  cd "$INSTALL_DIR"
  docker-compose down || true
  docker-compose up -d
  
  # Wait for service to be ready
  echo "Waiting for MCP Browser to be ready..."
  for i in {1..15}; do
    if curl -s "http://localhost:$PORT/api/status" | grep -q "ok"; then
      echo "MCP Browser is ready!"
      break
    fi
    
    if [ $i -eq 15 ]; then
      echo "MCP Browser failed to start. Check logs at: docker-compose logs"
      exit 1
    fi
    
    echo "Waiting... ($i/15)"
    sleep 5
  done
}

# Function to set up browser client
setup_browser_client() {
  echo "Setting up browser client..."
  
  # Create browser client HTML for testing
  mkdir -p "$HOME/.mcp-browser/client"
  cat > "$HOME/.mcp-browser/client/index.html" << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MCP Browser Client</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
    .container { max-width: 800px; margin: 0 auto; }
    .status { margin-bottom: 20px; padding: 10px; border-radius: 4px; }
    .connected { background-color: #d4edda; color: #155724; }
    .disconnected { background-color: #f8d7da; color: #721c24; }
    .event-log { height: 300px; overflow-y: auto; background-color: #f8f9fa; 
                 border: 1px solid #ddd; padding: 10px; border-radius: 4px; }
    button { background-color: #007bff; color: white; border: none; 
             padding: 8px 16px; border-radius: 4px; cursor: pointer; margin-right: 10px; }
    button:hover { background-color: #0069d9; }
    input { padding: 8px; margin-right: 10px; border: 1px solid #ddd; border-radius: 4px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>MCP Browser Client</h1>
    <div id="status" class="status disconnected">Disconnected</div>
    
    <div class="actions">
      <button id="connect">Connect</button>
      <button id="disconnect" disabled>Disconnect</button>
      <button id="subscribe" disabled>Subscribe to Events</button>
    </div>
    
    <h2>Browser Control</h2>
    <div class="browser-control">
      <input type="text" id="url" placeholder="https://example.com" value="https://example.com">
      <button id="navigate" disabled>Navigate</button>
      <button id="screenshot" disabled>Take Screenshot</button>
      <button id="back" disabled>Back</button>
      <button id="forward" disabled>Forward</button>
    </div>
    
    <h2>Event Log</h2>
    <div id="event-log" class="event-log"></div>
  </div>

  <script>
    // Get port from URL or use default
    const PORT = 7665;
    
    // DOM Elements
    const statusEl = document.getElementById('status');
    const eventLogEl = document.getElementById('event-log');
    const connectBtn = document.getElementById('connect');
    const disconnectBtn = document.getElementById('disconnect');
    const subscribeBtn = document.getElementById('subscribe');
    const navigateBtn = document.getElementById('navigate');
    const screenshotBtn = document.getElementById('screenshot');
    const backBtn = document.getElementById('back');
    const forwardBtn = document.getElementById('forward');
    const urlInput = document.getElementById('url');
    
    // WebSocket connection
    let socket = null;
    let eventSocket = null;
    
    // Log an event
    function logEvent(message, isError = false) {
      const item = document.createElement('div');
      item.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
      if (isError) {
        item.style.color = '#dc3545';
      }
      eventLogEl.appendChild(item);
      eventLogEl.scrollTop = eventLogEl.scrollHeight;
    }
    
    // Connect to WebSocket
    connectBtn.addEventListener('click', () => {
      // Connect to main WebSocket
      socket = new WebSocket(`ws://localhost:${PORT}/ws`);
      
      socket.onopen = () => {
        statusEl.textContent = 'Connected';
        statusEl.classList.remove('disconnected');
        statusEl.classList.add('connected');
        
        connectBtn.disabled = true;
        disconnectBtn.disabled = false;
        subscribeBtn.disabled = false;
        navigateBtn.disabled = false;
        screenshotBtn.disabled = false;
        backBtn.disabled = false;
        forwardBtn.disabled = false;
        
        logEvent('Connected to WebSocket');
      };
      
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        logEvent(`Received: ${JSON.stringify(data)}`);
      };
      
      socket.onclose = () => {
        statusEl.textContent = 'Disconnected';
        statusEl.classList.remove('connected');
        statusEl.classList.add('disconnected');
        
        connectBtn.disabled = false;
        disconnectBtn.disabled = true;
        subscribeBtn.disabled = true;
        navigateBtn.disabled = true;
        screenshotBtn.disabled = true;
        backBtn.disabled = true;
        forwardBtn.disabled = true;
        
        logEvent('Disconnected from WebSocket');
      };
      
      socket.onerror = (error) => {
        logEvent(`WebSocket Error: ${error}`, true);
      };
    });
    
    // Disconnect from WebSocket
    disconnectBtn.addEventListener('click', () => {
      if (socket) {
        socket.close();
      }
      
      if (eventSocket) {
        eventSocket.close();
      }
    });
    
    // Subscribe to events
    subscribeBtn.addEventListener('click', () => {
      // Connect to event WebSocket
      eventSocket = new WebSocket(`ws://localhost:${PORT}/ws/browser/events`);
      
      eventSocket.onopen = () => {
        logEvent('Connected to Event WebSocket');
        
        // Subscribe to all event types
        const subscribeMsg = {
          action: 'subscribe',
          event_types: ['PAGE', 'DOM', 'CONSOLE', 'NETWORK'],
          filters: { url_pattern: '*' }
        };
        
        eventSocket.send(JSON.stringify(subscribeMsg));
      };
      
      eventSocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        logEvent(`Event: ${JSON.stringify(data)}`);
      };
      
      eventSocket.onclose = () => {
        logEvent('Disconnected from Event WebSocket');
      };
      
      eventSocket.onerror = (error) => {
        logEvent(`Event WebSocket Error: ${error}`, true);
      };
    });
    
    // Navigate to URL
    navigateBtn.addEventListener('click', () => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        const url = urlInput.value;
        
        fetch(`http://localhost:${PORT}/api/browser/navigate`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ url, timeout: 30, wait_until: 'networkidle' }),
        })
        .then(response => response.json())
        .then(data => {
          logEvent(`Navigated to: ${url}`);
        })
        .catch((error) => {
          logEvent(`Navigation Error: ${error}`, true);
        });
      }
    });
    
    // Take screenshot
    screenshotBtn.addEventListener('click', () => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        fetch(`http://localhost:${PORT}/api/browser/screenshot`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ full_page: true }),
        })
        .then(response => response.json())
        .then(data => {
          if (data.image_data) {
            const img = document.createElement('img');
            img.src = `data:image/png;base64,${data.image_data}`;
            img.style.maxWidth = '100%';
            img.style.marginTop = '10px';
            
            const wrapper = document.createElement('div');
            wrapper.appendChild(img);
            
            eventLogEl.appendChild(wrapper);
            eventLogEl.scrollTop = eventLogEl.scrollHeight;
            
            logEvent('Screenshot taken');
          }
        })
        .catch((error) => {
          logEvent(`Screenshot Error: ${error}`, true);
        });
      }
    });
    
    // Go back
    backBtn.addEventListener('click', () => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        fetch(`http://localhost:${PORT}/api/browser/back`, {
          method: 'POST',
        })
        .then(response => response.json())
        .then(data => {
          logEvent('Navigated back');
        })
        .catch((error) => {
          logEvent(`Back Error: ${error}`, true);
        });
      }
    });
    
    // Go forward
    forwardBtn.addEventListener('click', () => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        fetch(`http://localhost:${PORT}/api/browser/forward`, {
          method: 'POST',
        })
        .then(response => response.json())
        .then(data => {
          logEvent('Navigated forward');
        })
        .catch((error) => {
          logEvent(`Forward Error: ${error}`, true);
        });
      }
    });
  </script>
</body>
</html>
EOF

  echo "Browser client is available at: file://$HOME/.mcp-browser/client/index.html"
}

# Function to display installation summary
show_summary() {
  IP_ADDRESS=$(ipconfig getifaddr en0 || echo "localhost")
  
  echo ""
  echo "========================================"
  echo "      MCP Browser Installation Complete"
  echo "========================================"
  echo ""
  echo "Server URL: http://$IP_ADDRESS:$PORT"
  echo "API Status: http://$IP_ADDRESS:$PORT/api/status"
  echo "WebSocket:  ws://$IP_ADDRESS:$PORT/ws"
  echo "Event WS:   ws://$IP_ADDRESS:$PORT/ws/browser/events"
  echo ""
  echo "Test Client: file://$HOME/.mcp-browser/client/index.html"
  echo ""
  echo "Connection Details:"
  echo "MCP Secret: $SECRET"
  echo ""
  echo "Installation Log: $LOG_FILE"
  echo ""
  echo "Connect your MCP client to this Mac using:"
  echo "IP: $IP_ADDRESS"
  echo "Port: $PORT"
  echo "Secret: $SECRET"
  echo ""
  echo "To stop the server: cd $INSTALL_DIR && docker-compose down"
  echo "To start the server: cd $INSTALL_DIR && docker-compose up -d"
  echo ""
  echo "========================================"
}

# Main installation function
main() {
  check_prerequisites
  setup_repository
  configure_environment
  start_services
  setup_browser_client
  show_summary
  
  echo "MCP Browser installation completed successfully!"
}

# Execute main function and log output
{
  main
} 2>&1 | tee -a "$LOG_FILE" 
#!/bin/bash
# Pi Monitor - Force Deployment Script
# Handles port conflicts, removes previous versions, and deploys latest with full cleanup

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="pi-mon"
COMPOSE_CMD="docker-compose"
COMPOSE_FILE="$COMPOSE_CMD.yml"
CONFLICTING_SERVICES=("redis" "redis-server" "mosquitto")
CONFLICTING_PORTS=(6379 1883 5001 80 9001)

# Docker Compose command setup
setup_compose_command() {
    # COMPOSE_CMD is already initialized to docker-compose at the top
    # This function will modify it based on dev/prod mode
    BASE_COMPOSE_CMD="docker-compose"
    
    if [[ "$DEV_MODE" == true ]]; then
        # Development mode - add dev overrides if they exist
        if [[ -f "${BASE_COMPOSE_CMD}.dev.yml" ]]; then
            COMPOSE_CMD="$BASE_COMPOSE_CMD -f ${BASE_COMPOSE_CMD}.yml -f ${BASE_COMPOSE_CMD}.dev.yml"
            log_verbose "Using development compose configuration"
        else
            log_verbose "Development mode requested but no ${BASE_COMPOSE_CMD}.dev.yml found"
        fi
        
        # Set development environment variables
        export NODE_ENV=development
        export REACT_APP_ENV=development
        export DEBUG=true
        export LOG_LEVEL=debug
        
    elif [[ "$PROD_MODE" == true ]]; then
        # Production mode - add prod overrides if they exist
        if [[ -f "${BASE_COMPOSE_CMD}.prod.yml" ]]; then
            COMPOSE_CMD="$BASE_COMPOSE_CMD -f ${BASE_COMPOSE_CMD}.yml -f ${BASE_COMPOSE_CMD}.prod.yml"
            log_verbose "Using production compose configuration"
        else
            log_verbose "Production mode requested but no ${BASE_COMPOSE_CMD}.prod.yml found"
        fi
        
        # Set production environment variables
        export NODE_ENV=production
        export REACT_APP_ENV=production
        export DEBUG=false
        export LOG_LEVEL=info
    fi
    
    log_verbose "Docker Compose command: $COMPOSE_CMD"
}

# Default flags
SKIP_CONFIRMATION=false
SKIP_CLEANUP=false
BUILD_ONLY=false
SHOW_LOGS=false
QUICK_MODE=false
VERBOSE=false
DEV_MODE=false
PROD_MODE=false
BACKEND_ONLY=false
FRONTEND_ONLY=false
SKIP_HEALTH_CHECK=false
PULL_IMAGES=true
CREATE_VENV=true

# Function to show help
show_help() {
    echo -e "${BLUE}🥧 Pi Monitor - Force Deployment Script${NC}"
    echo "============================================="
    echo ""
    echo "USAGE:"
    echo "  $0 [OPTIONS]"
    echo ""
    echo "DESCRIPTION:"
    echo "  Handles port conflicts, removes previous versions, and deploys"
    echo "  the latest Pi Monitor stack with full cleanup and health checks."
    echo ""
    echo -e "${CYAN}DEPLOYMENT OPTIONS:${NC}"
    echo "  -y, --yes                Skip confirmation prompts"
    echo "  -q, --quick              Quick mode - skip some checks for faster deployment"
    echo "  -v, --verbose            Enable verbose output and detailed logging"
    echo "  -d, --dev                Development mode - mount source code, enable debug"
    echo "  -p, --prod               Production mode - optimized settings and security"
    echo ""
    echo -e "${CYAN}BUILD OPTIONS:${NC}"
    echo "  -b, --build-only         Only build images, don't start services"
    echo "  -c, --no-cleanup         Skip the cleanup phase (faster, but may cause conflicts)"
    echo "      --no-pull            Skip pulling base images (use cached versions)"
    echo "      --no-venv            Skip creating Python virtual environment"
    echo ""
    echo -e "${CYAN}SERVICE OPTIONS:${NC}"
    echo "  -B, --backend-only       Deploy only backend services (Redis, MQTT, Backend)"
    echo "  -F, --frontend-only      Deploy only frontend service"
    echo "      --no-health-check    Skip health checks after deployment"
    echo ""
    echo -e "${CYAN}OUTPUT OPTIONS:${NC}"
    echo "  -l, --logs               Show service logs after deployment"
    echo "  -h, --help               Show this help message and exit"
    echo ""
    echo -e "${CYAN}EXAMPLES:${NC}"
    echo "  $0 -y -q                 # Quick deployment without prompts"
    echo "  $0 -d -l                 # Development deployment with logs"
    echo "  $0 -p -B                 # Production backend only"
    echo "  $0 -b                    # Just build images"
    echo "  $0 -c -v                 # Verbose mode without cleanup"
    echo "  $0 -y -q -F              # Quick frontend-only deployment"
    echo "  $0 -d -v -l              # Verbose development mode with logs"
    echo ""
    echo -e "${CYAN}MODES:${NC}"
    echo -e "  ${YELLOW}Development (--dev):${NC}"
    echo "    - Mounts source code for live editing"
    echo "    - Enables debug logging"
    echo "    - Uses development environment variables"
    echo "    - Hot reloading for frontend"
    echo ""
    echo -e "  ${YELLOW}Production (--prod):${NC}"
    echo "    - Optimized builds and security settings"
    echo "    - Production environment variables"
    echo "    - No debug output"
    echo "    - Compressed assets"
    echo ""
    echo -e "${CYAN}SERVICES DEPLOYED:${NC}"
    echo "  • Redis (Cache & Session Storage) - Port 6379"
    echo "  • Mosquitto MQTT Broker - Ports 1883, 9001"
    echo "  • Backend API (FastAPI) - Port 5001"
    echo "  • Frontend (React + Nginx) - Port 80"
    echo ""
    echo -e "${CYAN}POST-DEPLOYMENT:${NC}"
    NETWORK_IP=$(get_network_ip)
    echo "  Frontend:     http://localhost   or   http://$NETWORK_IP"
    echo "  Backend API:  http://localhost:5001   or   http://$NETWORK_IP:5001"
    echo "  Health Check: http://localhost:5001/health   or   http://$NETWORK_IP:5001/health"
    echo ""
    echo -e "${CYAN}QUICK REFERENCE (Shortcuts):${NC}"
    echo "  -y = --yes           -q = --quick         -v = --verbose"
    echo "  -d = --dev           -p = --prod          -l = --logs"
    echo "  -b = --build-only    -c = --no-cleanup    -h = --help"
    echo "  -B = --backend-only  -F = --frontend-only"
    echo ""
    exit 0
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                ;;
            -y|--yes)
                SKIP_CONFIRMATION=true
                shift
                ;;
            -c|--no-cleanup)
                SKIP_CLEANUP=true
                shift
                ;;
            -b|--build-only)
                BUILD_ONLY=true
                shift
                ;;
            -l|--logs)
                SHOW_LOGS=true
                shift
                ;;
            -q|--quick)
                QUICK_MODE=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -d|--dev)
                DEV_MODE=true
                shift
                ;;
            -p|--prod)
                PROD_MODE=true
                shift
                ;;
            -B|--backend-only)
                BACKEND_ONLY=true
                shift
                ;;
            -F|--frontend-only)
                FRONTEND_ONLY=true
                shift
                ;;
            --no-health-check)
                SKIP_HEALTH_CHECK=true
                shift
                ;;
            --no-pull)
                PULL_IMAGES=false
                shift
                ;;
            --no-venv)
                CREATE_VENV=false
                shift
                ;;
            *)
                echo -e "${RED}❌ Unknown option: $1${NC}"
                echo "Use --help for usage information."
                exit 1
                ;;
        esac
    done

    # Validate mutually exclusive options
    if [[ "$DEV_MODE" == true && "$PROD_MODE" == true ]]; then
        echo -e "${RED}❌ Cannot use both --dev and --prod modes${NC}"
        exit 1
    fi

    if [[ "$BACKEND_ONLY" == true && "$FRONTEND_ONLY" == true ]]; then
        echo -e "${RED}❌ Cannot use both --backend-only and --frontend-only${NC}"
        exit 1
    fi
}

# Verbose logging function
log_verbose() {
    if [[ "$VERBOSE" == true ]]; then
        echo -e "${CYAN}[VERBOSE]${NC} $1"
    fi
}

# Parse command line arguments first
parse_arguments "$@"

# Setup Docker Compose command based on mode
setup_compose_command

echo -e "${BLUE}🥧 Pi Monitor - Force Deployment${NC}"
echo "=================================="

# Show mode information
if [[ "$DEV_MODE" == true ]]; then
    echo -e "${YELLOW}🔧 Development Mode Enabled${NC}"
elif [[ "$PROD_MODE" == true ]]; then
    echo -e "${GREEN}🏭 Production Mode Enabled${NC}"
fi

# Show what will be deployed
if [[ "$BACKEND_ONLY" == true ]]; then
    echo -e "${BLUE}📡 Backend-only deployment${NC}"
elif [[ "$FRONTEND_ONLY" == true ]]; then
    echo -e "${BLUE}🌐 Frontend-only deployment${NC}"
else
    echo -e "${BLUE}🔄 Full stack deployment${NC}"
fi

if [[ "$SKIP_CLEANUP" == false ]]; then
    echo -e "${YELLOW}⚠️  This will completely remove all existing pi-mon containers, images, and volumes!${NC}"
fi
echo ""

# Ask for confirmation unless --yes flag is provided
if [[ "$SKIP_CONFIRMATION" == false ]]; then
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled."
        exit 0
    fi
fi

echo ""
echo -e "${PURPLE}🔍 System Information:${NC}"
echo "Architecture: $(uname -m)"
echo "OS: $(cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d'"' -f2 || echo 'Unknown')"
echo "Docker version: $(docker --version 2>/dev/null || echo 'Not installed')"
echo "Docker Compose version: $($COMPOSE_CMD --version 2>/dev/null || echo 'Not installed')"
echo ""

# Function to check if a port is in use
check_port() {
    local port=$1
    if netstat -tuln 2>/dev/null | grep -q ":$port " || ss -tuln 2>/dev/null | grep -q ":$port "; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to find what's using a port
find_port_user() {
    local port=$1
    echo "Port $port usage:"
    netstat -tulpn 2>/dev/null | grep ":$port " || ss -tulpn 2>/dev/null | grep ":$port " || echo "  No specific process found"
}

# Function to get the Pi's network IP address
get_network_ip() {
    # Try multiple methods to get the network IP
    local ip=""
    
    # Method 1: ip route (most reliable)
    ip=$(ip route get 8.8.8.8 2>/dev/null | grep -oP 'src \K[^\s]+' | head -1)
    
    # Method 2: hostname -I (fallback)
    if [[ -z "$ip" ]]; then
        ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    fi
    
    # Method 3: ifconfig (legacy fallback)
    if [[ -z "$ip" ]]; then
        ip=$(ifconfig 2>/dev/null | grep 'inet ' | grep -v '127.0.0.1' | awk '{print $2}' | head -1)
    fi
    
    # Default fallback
    if [[ -z "$ip" ]]; then
        ip="<Pi-IP>"
    fi
    
    echo "$ip"
}

# Function to stop system services safely
stop_system_service() {
    local service=$1
    if systemctl is-active --quiet "$service" 2>/dev/null; then
        echo -e "${YELLOW}  🛑 Stopping system service: $service${NC}"
        sudo systemctl stop "$service" || echo -e "${RED}    ❌ Failed to stop $service${NC}"
        
        # Also disable it to prevent auto-restart
        if systemctl is-enabled --quiet "$service" 2>/dev/null; then
            echo -e "${YELLOW}  🚫 Disabling auto-start for: $service${NC}"
            sudo systemctl disable "$service" || echo -e "${RED}    ❌ Failed to disable $service${NC}"
        fi
    fi
}

# Step 1: Check for Docker and Docker Compose
echo -e "${BLUE}📦 Checking Docker installation...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed!${NC}"
    echo "Please install Docker first: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

if ! command -v $COMPOSE_CMD &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed!${NC}"
    echo "Please install Docker Compose first."
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker daemon is not running!${NC}"
    echo "Please start Docker: sudo systemctl start docker"
    exit 1
fi

echo -e "${GREEN}✅ Docker and Docker Compose are ready${NC}"

# Step 2: Check for $COMPOSE_CMD.yml
if [[ ! -f "$COMPOSE_FILE" ]]; then
    echo -e "${RED}❌ $COMPOSE_FILE not found!${NC}"
    echo "Please run this script from the pi-mon directory."
    exit 1
fi

# Step 3: Stop conflicting system services (unless in quick mode)
if [[ "$QUICK_MODE" == false ]]; then
    echo ""
    echo -e "${BLUE}🔍 Checking for conflicting system services...${NC}"
    for service in "${CONFLICTING_SERVICES[@]}"; do
        log_verbose "Checking service: $service"
        stop_system_service "$service"
    done
else
    log_verbose "Skipping system service checks (quick mode)"
fi

# Step 4: Check for port conflicts (unless in quick mode)
if [[ "$QUICK_MODE" == false ]]; then
    echo ""
    echo -e "${BLUE}🔌 Checking for port conflicts...${NC}"
    conflicts_found=false
    for port in "${CONFLICTING_PORTS[@]}"; do
        log_verbose "Checking port: $port"
        if check_port "$port"; then
            echo -e "${YELLOW}⚠️  Port $port is in use:${NC}"
            find_port_user "$port"
            conflicts_found=true
        fi
    done
else
    log_verbose "Skipping port conflict checks (quick mode)"
    conflicts_found=false
fi

if [[ "$conflicts_found" == true ]]; then
    echo ""
    echo -e "${YELLOW}⚠️  Some ports are still in use. Attempting to resolve...${NC}"
    
    # Try to kill processes using our ports (be careful here)
    for port in "${CONFLICTING_PORTS[@]}"; do
        if check_port "$port"; then
            echo -e "${YELLOW}  🔧 Attempting to free port $port...${NC}"
            # Find and kill processes using these specific ports (only if they're likely ours)
            pids=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1 | grep -E '^[0-9]+$' || true)
            if [[ -n "$pids" ]]; then
                for pid in $pids; do
                    if ps -p "$pid" -o comm= 2>/dev/null | grep -E "(redis|mosquitto|python)" &>/dev/null; then
                        echo -e "${YELLOW}    🔪 Killing process $pid using port $port${NC}"
                        sudo kill -TERM "$pid" 2>/dev/null || true
                        sleep 2
                        sudo kill -KILL "$pid" 2>/dev/null || true
                    fi
                done
            fi
        fi
    done
    
    # Wait a moment for processes to fully terminate
    echo -e "${BLUE}  ⏳ Waiting for processes to terminate...${NC}"
    sleep 3
    
    # Verify ports are now free
    echo ""
    echo -e "${BLUE}🔍 Verifying ports are now free...${NC}"
    remaining_conflicts=false
    for port in "${CONFLICTING_PORTS[@]}"; do
        if check_port "$port"; then
            echo -e "${RED}  ❌ Port $port is still in use after cleanup attempt${NC}"
            find_port_user "$port"
            remaining_conflicts=true
        else
            echo -e "${GREEN}  ✅ Port $port is now free${NC}"
        fi
    done
    
    # If ports are still in use, warn user but continue (they might be using different ports)
    if [[ "$remaining_conflicts" == true ]]; then
        echo ""
        echo -e "${RED}⚠️  WARNING: Some ports are still in use!${NC}"
        echo -e "${YELLOW}This deployment will continue, but may fail if these ports conflict with your services.${NC}"
        echo -e "${YELLOW}Consider checking your docker-compose.yml port mappings or stopping the conflicting processes manually.${NC}"
        
        if [[ "$SKIP_CONFIRMATION" == false ]]; then
            echo ""
            read -p "Do you want to continue anyway? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "Deployment cancelled due to port conflicts."
                exit 1
            fi
        fi
    else
        echo -e "${GREEN}✅ All port conflicts resolved successfully${NC}"
    fi
fi

# Step 5: Complete Docker cleanup (unless --no-cleanup)
if [[ "$SKIP_CLEANUP" == false ]]; then
    echo ""
    echo -e "${BLUE}🧹 Performing complete Docker cleanup...${NC}"

    # Stop all pi-mon containers
    log_verbose "Stopping containers..."
    echo -e "${YELLOW}  🛑 Stopping all pi-mon containers...${NC}"
    $COMPOSE_CMD down --remove-orphans || echo "No containers to stop"

    # Remove all pi-mon containers (including stopped ones)
    containers=$(docker ps -aq --filter "name=$PROJECT_NAME" 2>/dev/null || true)
    if [[ -n "$containers" ]]; then
        log_verbose "Found containers to remove: $containers"
        echo -e "${YELLOW}  🗑️  Removing all pi-mon containers...${NC}"
        docker rm -f $containers || echo "Some containers couldn't be removed"
    fi

    # Remove all pi-mon images
    images=$(docker images --filter "reference=*$PROJECT_NAME*" -q 2>/dev/null || true)
    if [[ -n "$images" ]]; then
        log_verbose "Found images to remove: $images"
        echo -e "${YELLOW}  🗑️  Removing all pi-mon images...${NC}"
        docker rmi -f $images || echo "Some images couldn't be removed"
    fi

    # Remove all pi-mon volumes
    volumes=$(docker volume ls --filter "name=$PROJECT_NAME" -q 2>/dev/null || true)
    if [[ -n "$volumes" ]]; then
        log_verbose "Found volumes to remove: $volumes"
        echo -e "${YELLOW}  🗑️  Removing all pi-mon volumes...${NC}"
        docker volume rm $volumes || echo "Some volumes couldn't be removed"
    fi

    # Remove specific volumes from $COMPOSE_CMD
    echo -e "${YELLOW}  🗑️  Removing compose volumes...${NC}"
    $COMPOSE_CMD down -v --remove-orphans || true

    # Clean up Docker system
    echo -e "${YELLOW}  🧽 Cleaning Docker system...${NC}"
    docker system prune -f --volumes || true

    echo -e "${GREEN}✅ Docker cleanup completed${NC}"
else
    echo ""
    echo -e "${YELLOW}⏩ Skipping cleanup phase (--no-cleanup flag)${NC}"
    # Still stop containers for deployment
    $COMPOSE_CMD down --remove-orphans || echo "No containers to stop"
fi

# Step 6: Build and deploy
echo ""
echo -e "${BLUE}🏗️  Building and deploying latest version...${NC}"

# Set compose command based on service selection
COMPOSE_SERVICES=""
if [[ "$BACKEND_ONLY" == true ]]; then
    COMPOSE_SERVICES="redis mosquitto backend"
    log_verbose "Services: $COMPOSE_SERVICES"
elif [[ "$FRONTEND_ONLY" == true ]]; then
    COMPOSE_SERVICES="frontend"
    log_verbose "Services: $COMPOSE_SERVICES"
fi

# Pull latest images (unless --no-pull)
if [[ "$PULL_IMAGES" == true ]]; then
    echo -e "${YELLOW}  📥 Pulling latest base images...${NC}"
    if [[ -n "$COMPOSE_SERVICES" ]]; then
        $COMPOSE_CMD pull $COMPOSE_SERVICES || echo "Pull completed with warnings"
    else
        $COMPOSE_CMD pull || echo "Pull completed with warnings"
    fi
else
    echo -e "${YELLOW}⏩ Skipping image pull (--no-pull flag)${NC}"
fi

# Prepare build arguments based on mode
BUILD_ARGS="--no-cache"
if [[ "$PULL_IMAGES" == true ]]; then
    BUILD_ARGS="$BUILD_ARGS --pull"
fi

# Build the application
echo -e "${YELLOW}  🔨 Building application images...${NC}"
if [[ -n "$COMPOSE_SERVICES" ]]; then
    log_verbose "Building services: $COMPOSE_SERVICES"
    $COMPOSE_CMD build $BUILD_ARGS $COMPOSE_SERVICES
else
    log_verbose "Building all services"
    $COMPOSE_CMD build $BUILD_ARGS
fi

# Step 7: Create Python virtual environment for host tools (unless --no-venv)
if [[ "$CREATE_VENV" == true ]]; then
    echo ""
    echo -e "${BLUE}🐍 Setting up Python virtual environment for host tools...${NC}"
    if command -v python3 &>/dev/null; then
        if [[ ! -d "venv" ]]; then
            log_verbose "Creating new virtual environment"
            echo -e "${YELLOW}  📦 Creating virtual environment...${NC}"
            python3 -m venv venv
        else
            log_verbose "Virtual environment already exists"
        fi
        
        if [[ -f "backend/requirements.txt" ]]; then
            echo -e "${YELLOW}  📥 Installing Python packages in venv...${NC}"
            venv/bin/pip install --upgrade pip --quiet
            venv/bin/pip install -r backend/requirements.txt --quiet
            echo -e "${GREEN}    ✅ Python packages installed in venv${NC}"
        fi
    else
        echo -e "${YELLOW}    ⚠️  Python3 not found - skipping host venv setup${NC}"
    fi
else
    echo ""
    echo -e "${YELLOW}⏩ Skipping virtual environment setup (--no-venv flag)${NC}"
fi

# Exit if build-only mode
if [[ "$BUILD_ONLY" == true ]]; then
    echo ""
    echo -e "${GREEN}🎉 Build-only deployment complete!${NC}"
    echo -e "${BLUE}Images built successfully. Use '$COMPOSE_CMD up -d' to start services.${NC}"
    exit 0
fi

# Step 8: Start services
echo ""
echo -e "${BLUE}🚀 Starting services...${NC}"
if [[ -n "$COMPOSE_SERVICES" ]]; then
    log_verbose "Starting services: $COMPOSE_SERVICES"
    $COMPOSE_CMD up -d $COMPOSE_SERVICES
else
    log_verbose "Starting all services"
    $COMPOSE_CMD up -d
fi

# Step 9: Wait and perform health checks (unless --no-health-check)
if [[ "$SKIP_HEALTH_CHECK" == false ]]; then
    echo ""
    echo -e "${BLUE}🏥 Performing health checks...${NC}"
    
    # Shorter wait in quick mode
    if [[ "$QUICK_MODE" == true ]]; then
        sleep 5
    else
        sleep 10
    fi

    # Check if containers are running
    echo -e "${YELLOW}  📊 Checking container status...${NC}"
    if [[ -n "$COMPOSE_SERVICES" ]]; then
        $COMPOSE_CMD ps $COMPOSE_SERVICES
    else
        $COMPOSE_CMD ps
    fi

    # Detailed health checks
    echo ""
    echo -e "${YELLOW}  🩺 Running detailed health checks...${NC}"

    # Check Redis (if not frontend-only)
    if [[ "$FRONTEND_ONLY" == false ]] && $COMPOSE_CMD ps redis | grep -q "Up"; then
        log_verbose "Testing Redis connectivity"
        if $COMPOSE_CMD exec -T redis redis-cli ping &>/dev/null; then
            echo -e "${GREEN}    ✅ Redis is healthy${NC}"
        else
            echo -e "${RED}    ❌ Redis health check failed${NC}"
        fi
    fi

    # Check Mosquitto (if not frontend-only)
    if [[ "$FRONTEND_ONLY" == false ]] && $COMPOSE_CMD ps mosquitto | grep -q "Up"; then
        log_verbose "Testing Mosquitto connectivity"
        if $COMPOSE_CMD exec -T mosquitto mosquitto_pub -h localhost -t test -m "health_check" &>/dev/null; then
            echo -e "${GREEN}    ✅ Mosquitto is healthy${NC}"
        else
            echo -e "${YELLOW}    ⚠️  Mosquitto health check inconclusive${NC}"
        fi
    fi

    # Check Backend (if not frontend-only)
    if [[ "$FRONTEND_ONLY" == false ]] && $COMPOSE_CMD ps backend | grep -q "Up"; then
        echo -e "${YELLOW}    🔍 Testing backend...${NC}"
        sleep 5
        log_verbose "Testing backend API at http://localhost:5001/health"
        if curl -f -s http://localhost:5001/health &>/dev/null; then
            echo -e "${GREEN}    ✅ Backend is healthy and responding${NC}"
        else
            echo -e "${YELLOW}    ⚠️  Backend health check failed - checking logs...${NC}"
            $COMPOSE_CMD logs backend --tail=10
        fi
    fi

    # Check Frontend (if not backend-only)
    if [[ "$BACKEND_ONLY" == false ]] && $COMPOSE_CMD ps frontend | grep -q "Up"; then
        echo -e "${YELLOW}    🔍 Testing frontend...${NC}"
        log_verbose "Testing frontend at http://localhost:80"
        if curl -f -s http://localhost:80/ &>/dev/null; then
            echo -e "${GREEN}    ✅ Frontend is healthy and responding${NC}"
        else
            echo -e "${YELLOW}    ⚠️  Frontend health check failed - checking logs...${NC}"
            $COMPOSE_CMD logs frontend --tail=10
        fi
    fi
else
    echo ""
    echo -e "${YELLOW}⏩ Skipping health checks (--no-health-check flag)${NC}"
fi

# Step 10: Final verification
echo ""
echo -e "${BLUE}📋 Final verification...${NC}"

# Show container status
echo ""
echo -e "${CYAN}📊 Container Status:${NC}"
$COMPOSE_CMD ps

# Show port usage
echo ""
echo -e "${CYAN}🔌 Port Status:${NC}"
for port in "${CONFLICTING_PORTS[@]}"; do
    if check_port "$port"; then
        echo -e "${GREEN}  ✅ Port $port: In use (by pi-mon)${NC}"
    else
        echo -e "${RED}  ❌ Port $port: Not in use${NC}"
    fi
done

# Show logs summary or detailed logs if requested
if [[ "$SHOW_LOGS" == true ]]; then
    echo ""
    echo -e "${CYAN}📝 Detailed Service Logs:${NC}"
    if [[ -n "$COMPOSE_SERVICES" ]]; then
        $COMPOSE_CMD logs --tail=20 $COMPOSE_SERVICES
    else
        $COMPOSE_CMD logs --tail=20
    fi
else
    echo ""
    echo -e "${CYAN}📝 Recent Logs Summary:${NC}"
    if [[ -n "$COMPOSE_SERVICES" ]]; then
        $COMPOSE_CMD logs --tail=3 $COMPOSE_SERVICES
    else
        $COMPOSE_CMD logs --tail=3
    fi
fi

# Show deployment completion message
echo ""
echo -e "${GREEN}🎉 Pi Monitor Force Deployment Complete!${NC}"

# Show deployment type
if [[ "$BACKEND_ONLY" == true ]]; then
    echo -e "${BLUE}📡 Backend-only deployment completed${NC}"
elif [[ "$FRONTEND_ONLY" == true ]]; then
    echo -e "${BLUE}🌐 Frontend-only deployment completed${NC}"
else
    echo -e "${BLUE}🔄 Full stack deployment completed${NC}"
fi

# Show mode
if [[ "$DEV_MODE" == true ]]; then
    echo -e "${YELLOW}🔧 Development mode active${NC}"
elif [[ "$PROD_MODE" == true ]]; then
    echo -e "${GREEN}🏭 Production mode active${NC}"
fi

echo ""
echo -e "${CYAN}📊 Deployment Information:${NC}"

# Get network IP for URLs
NETWORK_IP=$(get_network_ip)

# Show URLs based on what was deployed
if [[ "$BACKEND_ONLY" == false ]]; then
    echo "  Frontend URL:    http://localhost:80   or   http://$NETWORK_IP:80"
fi
if [[ "$FRONTEND_ONLY" == false ]]; then
    echo "  Backend API:     http://localhost:5001   or   http://$NETWORK_IP:5001"
    echo "  Backend Health:  http://localhost:5001/health   or   http://$NETWORK_IP:5001/health"
    echo "  Redis Port:      6379"
    echo "  MQTT Port:       1883"
    echo "  MQTT WebSocket:  9001"
fi
echo ""
echo -e "${CYAN}🛠️  Useful Commands:${NC}"

# Base commands
if [[ -n "$COMPOSE_SERVICES" ]]; then
    echo "  View logs:       $COMPOSE_CMD logs -f $COMPOSE_SERVICES"
    echo "  View status:     $COMPOSE_CMD ps $COMPOSE_SERVICES"
    echo "  Stop services:   $COMPOSE_CMD down"
    echo "  Restart:         $COMPOSE_CMD restart $COMPOSE_SERVICES"
else
    echo "  View logs:       $COMPOSE_CMD logs -f"
    echo "  View status:     $COMPOSE_CMD ps"
    echo "  Stop all:        $COMPOSE_CMD down"
    echo "  Restart:         $COMPOSE_CMD restart"
fi

# Redeploy commands based on current flags
REDEPLOY_CMD="./force_deploy.sh"
[[ "$SKIP_CONFIRMATION" == true ]] && REDEPLOY_CMD="$REDEPLOY_CMD --yes"
[[ "$QUICK_MODE" == true ]] && REDEPLOY_CMD="$REDEPLOY_CMD --quick"
[[ "$DEV_MODE" == true ]] && REDEPLOY_CMD="$REDEPLOY_CMD --dev"
[[ "$PROD_MODE" == true ]] && REDEPLOY_CMD="$REDEPLOY_CMD --prod"
[[ "$BACKEND_ONLY" == true ]] && REDEPLOY_CMD="$REDEPLOY_CMD --backend-only"
[[ "$FRONTEND_ONLY" == true ]] && REDEPLOY_CMD="$REDEPLOY_CMD --frontend-only"

echo "  Force redeploy:  $REDEPLOY_CMD"
echo "  Quick redeploy:  ./force_deploy.sh --yes --quick --no-cleanup"

# Service-specific commands based on what was deployed
if [[ "$SKIP_CLEANUP" == false || "$BACKEND_ONLY" == false ]]; then
    echo ""
    echo -e "${CYAN}🔧 Service-specific Commands:${NC}"
    
    [[ "$FRONTEND_ONLY" == false ]] && echo "  Backend logs:    $COMPOSE_CMD logs backend -f"
    [[ "$BACKEND_ONLY" == false ]] && echo "  Frontend logs:   $COMPOSE_CMD logs frontend -f"
    [[ "$FRONTEND_ONLY" == false ]] && echo "  Redis logs:      $COMPOSE_CMD logs redis -f"
    [[ "$FRONTEND_ONLY" == false ]] && echo "  MQTT logs:       $COMPOSE_CMD logs mosquitto -f"
fi
echo ""
echo -e "${CYAN}📱 Testing:${NC}"

# Get network IP for testing commands
NETWORK_IP=$(get_network_ip)

# Test commands based on what was deployed
if [[ "$FRONTEND_ONLY" == false ]]; then
    echo "  Test backend:    curl http://localhost:5001/health   or   curl http://$NETWORK_IP:5001/health"
    echo "  Test Redis:      $COMPOSE_CMD exec redis redis-cli ping"
    echo "  Test MQTT:       $COMPOSE_CMD exec mosquitto mosquitto_pub -h localhost -t test -m hello"
fi

if [[ "$BACKEND_ONLY" == false ]]; then
    echo "  Test frontend:   curl http://localhost:80   or   curl http://$NETWORK_IP:80"
fi

# Python Virtual Environment section (if created)
if [[ "$CREATE_VENV" == true ]]; then
    echo ""
    echo -e "${CYAN}🐍 Python Virtual Environment (for host commands):${NC}"
    if [[ -d "venv" ]]; then
        echo "  Virtual env:     source venv/bin/activate"
        echo "  Run agent:       venv/bin/python backend/agent.py"
        echo "  Install package: venv/bin/pip install <package>"
        echo "  Deactivate:      deactivate"
    else
        echo "  Not created - run deployment again to set up venv"
    fi
fi

# Mode-specific information
if [[ "$DEV_MODE" == true ]]; then
    echo ""
    echo -e "${YELLOW}🔧 Development Mode Tips:${NC}"
    echo "  • Source code is mounted for live editing"
    echo "  • Debug logging is enabled"
    echo "  • Hot reloading is active for frontend"
    echo "  • Use '--logs' flag to monitor development output"
elif [[ "$PROD_MODE" == true ]]; then
    echo ""
    echo -e "${GREEN}🏭 Production Mode Notes:${NC}"
    echo "  • Optimized builds and security settings active"
    echo "  • Debug output is disabled"
    echo "  • Assets are compressed"
    echo "  • Monitor logs regularly for issues"
fi

echo ""
echo -e "${CYAN}🚀 Advanced Usage:${NC}"
echo "  Build only:      ./force_deploy.sh -b"
echo "  Quick deploy:    ./force_deploy.sh -y -q -c"
echo "  Dev mode:        ./force_deploy.sh -d -l"
echo "  Backend only:    ./force_deploy.sh -B -y"
echo "  Frontend only:   ./force_deploy.sh -F -y"
echo "  Verbose mode:    ./force_deploy.sh -v -l"
echo "  Production:      ./force_deploy.sh -p -y"
echo ""

# Final status check
echo -e "${BLUE}🔍 Final Status Check:${NC}"

if [[ -n "$COMPOSE_SERVICES" ]]; then
    if $COMPOSE_CMD ps $COMPOSE_SERVICES | grep -q "Up"; then
        echo -e "${GREEN}✨ Deployment successful! Selected services are running.${NC}"
        exit 0
    else
        echo -e "${RED}⚠️  Some selected services may not be running properly. Check logs above.${NC}"
        $COMPOSE_CMD ps $COMPOSE_SERVICES
        exit 1
    fi
else
    if $COMPOSE_CMD ps | grep -q "Up"; then
        echo -e "${GREEN}✨ Deployment successful! All services are running.${NC}"
        exit 0
    else
        echo -e "${RED}⚠️  Some services may not be running properly. Check logs above.${NC}"
        $COMPOSE_CMD ps
        exit 1
    fi
fi

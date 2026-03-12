#!/bin/bash
# 7Flow Bot v2.0 - Premium Setup & Configuration
# Interactive setup with enhanced AI provider selection

set -e

# === Color Palette ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# === UI Functions ===
show_header() {
    clear
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}7FLOW BOT v2.0${NC}                                  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${DIM}Professional Polymarket Trading System${NC}            ${CYAN}║${NC}"
    echo -e "${CYAN}╠══════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  ${PURPLE}AI-Powered${NC} | ${YELLOW}Multi-Strategy${NC} | ${GREEN}Real-Time${NC}        ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_step() {
    echo -e "${PURPLE}━━━${NC} ${CYAN}[$1]${NC} ${WHITE}$2${NC}"
}

print_success() {
    echo -e "     ${GREEN}✓${NC} ${DIM}$1${NC}"
}

print_error() {
    echo -e "     ${RED}✗${NC} ${RED}$1${NC}"
}

print_info() {
    echo -e "     ${BLUE}ℹ${NC} ${DIM}$1${NC}"
}

# === Step 1: Environment Setup ===
setup_environment() {
    print_step "01" "Setting up Python environment"
    
    if [ ! -d ".venv" ]; then
        echo -ne "     Creating virtual environment... "
        python3 -m venv .venv
        echo -e "${GREEN}Done${NC}"
    fi
    
    source .venv/bin/activate
    print_success "Virtual environment activated"
    
    echo -ne "     Upgrading pip... "
    pip install --upgrade pip -q
    echo -e "${GREEN}Done${NC}"
}

# === Step 2: Install Dependencies ===
install_dependencies() {
    print_step "02" "Installing trading & AI dependencies"
    
    echo -ne "     Installing core packages... "
    pip install -e . -q 2>/dev/null
    
    # Enhanced AI & trading packages
    pip install -q \
        textual \
        httpx[http2] \
        vertexai \
        openai \
        anthropic \
        groq \
        huggingface_hub \
        google-cloud-aiplatform \
        fastapi \
        uvicorn \
        jinja2 \
        python-multipart \
        web3 \
        eth-account \
        py-clob-client \
        aiosqlite \
        rich \
        click \
        ccxt \
        playwright \
        playwright-stealth \
        2>/dev/null
    
    echo -ne "     Installing browser drivers... "
    playwright install chromium -q 2>/dev/null
    echo -e "${GREEN}Done${NC}"
    
    echo -e "${GREEN}Done${NC}"
    print_success "All dependencies installed"
}

# === Step 3: Wallet Configuration ===
configure_wallet() {
    print_step "03" "Wallet Configuration"
    echo ""
    echo -e "     ${DIM}Enter your Polygon wallet credentials:${NC}"
    echo -e "     ${YELLOW}Tip:${NC} Get your private key from MetaMask Settings > Security & Privacy"
    echo ""
    
    # Wallet Address
    while true; do
        echo -ne "     ${CYAN}Wallet Address${NC} (0x...): "
        read WALLET_ADDR
        
        if [[ $WALLET_ADDR =~ ^0x[a-fA-F0-9]{40}$ ]]; then
            print_success "Wallet address valid"
            break
        else
            print_error "Invalid address. Must be 0x + 40 hex characters"
        fi
    done
    
    # Private Key
    while true; do
        echo -ne "     ${CYAN}Private Key${NC} (0x...): "
        read -s PRIV_KEY
        echo ""
        
        if [[ $PRIV_KEY =~ ^0x[a-fA-F0-9]{64}$ ]]; then
            print_success "Private key valid"
            break
        else
            print_error "Invalid key. Must be 0x + 64 hex characters"
        fi
    done
    
    # Polymarket Credentials
    echo ""
    echo -e "     ${DIM}Polymarket L2 API Credentials:${NC}"
    echo -e "     ${YELLOW}Tip:${NC} Create these in Polymarket Settings > API"
    echo -ne "     API Key: "
    read POLY_KEY
    echo -ne "     API Secret: "
    read -s POLY_SECRET
    echo ""
    echo -ne "     API Passphrase: "
    read -s POLY_PASS
    echo ""
}

# === Step 4: AI Provider Selection ===
configure_ai() {
    print_step "04" "AI Intelligence Engine"
    echo ""
    echo -e "     ${BOLD}Select your AI provider:${NC}"
    echo ""
    echo -e "     ${CYAN}1)${NC} Standard       ${DIM}- Math-only arbitrage (no AI)${NC}"
    echo -e "     ${PURPLE}2)${NC} Google Gemini  ${DIM}- Vertex AI, high logic${NC}"
    echo -e "     ${BLUE}3)${NC} OpenAI         ${DIM}- GPT-4o, GPT-4o-mini, o1${NC}"
    echo -e "     ${YELLOW}4)${NC} Anthropic      ${DIM}- Claude 3.5 Sonnet${NC}"
    echo -e "     ${GREEN}5)${NC} Groq           ${DIM}- Ultra-fast Llama-3.1${NC}"
    echo -e "     ${RED}6)${NC} OpenRouter     ${DIM}- 50+ models${NC}"
    echo -e "     ${DIM}7)${NC} NVIDIA         ${DIM}- Nemotron models${NC}"
    echo -e "     ${DIM}8)${NR} HuggingFace    ${DIM}- Open-source LLMs${NC}"
    echo -e "     ${DIM}9)${NC} xAI            ${DIM}- Grok (Elon's AI)${NC}"
    echo -e "     ${DIM}10)${NC} Local AI       ${DIM}- Ollama / LM Studio${NC}"
    echo ""
    echo -ne "     ${CYAN}Select provider${NC} [1-10]: "
    read AI_CHOICE
    
    case $AI_CHOICE in
        1)
            AI_TYPE="standard"
            print_info "Using mathematical arbitrage only"
            ;;
        2)
            AI_TYPE="gemini"
            echo -e "     ${YELLOW}Tutorial:${NC} Get Gemini keys at https://aistudio.google.com"
            echo -ne "     Google Cloud Project ID: "
            read GCP_PROJECT
            echo -ne "     Gemini API Key: "
            read -s GEMINI_KEY
            echo ""
            print_info "Using Vertex AI - Gemini"
            ;;
        3)
            AI_TYPE="openai"
            echo -e "     ${YELLOW}Tutorial:${NC} Get OpenAI keys at https://platform.openai.com"
            echo -ne "     OpenAI Model [gpt-4o]: "
            read OAI_MODEL
            [[ -z $OAI_MODEL ]] && OAI_MODEL="gpt-4o"
            echo -ne "     OpenAI API Key: "
            read -s OAI_KEY
            echo ""
            print_info "Using OpenAI - $OAI_MODEL"
            ;;
        4)
            AI_TYPE="anthropic"
            echo -e "     ${YELLOW}Tutorial:${NC} Get Anthropic keys at https://console.anthropic.com"
            echo -ne "     Anthropic Model [claude-3-5-sonnet]: "
            read ANT_MODEL
            [[ -z $ANT_MODEL ]] && ANT_MODEL="claude-3-5-sonnet-20241022"
            echo -ne "     Anthropic API Key: "
            read -s ANT_KEY
            echo ""
            print_info "Using Anthropic - $ANT_MODEL"
            ;;
        5)
            AI_TYPE="groq"
            echo -e "     ${YELLOW}Tutorial:${NC} Get Groq keys at https://console.groq.com"
            echo -ne "     Groq Model [llama-3.1-70b]: "
            read GROQ_MODEL
            [[ -z $GROQ_MODEL ]] && GROQ_MODEL="llama-3.1-70b-versatile"
            echo -ne "     Groq API Key: "
            read -s GROQ_KEY
            echo ""
            print_info "Using Groq - $GROQ_MODEL (Ultra-fast)"
            ;;
        6)
            AI_TYPE="openrouter"
            echo -e "     ${YELLOW}Tutorial:${NC} Get OpenRouter keys at https://openrouter.ai/settings/keys"
            echo -ne "     OpenRouter Model: "
            read OR_MODEL
            [[ -z $OR_MODEL ]] && OR_MODEL="meta-llama/llama-3.1-405b-instruct"
            echo -ne "     OpenRouter API Key: "
            read -s OR_KEY
            echo ""
            print_info "Using OpenRouter - $OR_MODEL"
            ;;
        7)
            AI_TYPE="nvidia"
            echo -e "     ${YELLOW}Tutorial:${NC} Get NVIDIA keys at https://build.nvidia.com"
            echo -ne "     NVIDIA Model: "
            read NV_MODEL
            [[ -z $NV_MODEL ]] && NV_MODEL="nvidia/llama-3.1-nemotron-70b-instruct"
            echo -ne "     NVIDIA API Key: "
            read -s NV_KEY
            echo ""
            print_info "Using NVIDIA - $NV_MODEL"
            ;;
        8)
            AI_TYPE="huggingface"
            echo -e "     ${YELLOW}Tutorial:${NC} Get HF keys at https://huggingface.co/settings/tokens"
            echo -ne "     HuggingFace Model: "
            read HF_MODEL
            [[ -z $HF_MODEL ]] && HF_MODEL="meta-llama/Llama-3.1-70B-Instruct"
            echo -ne "     HuggingFace API Key: "
            read -s HF_KEY
            echo ""
            print_info "Using HuggingFace - $HF_MODEL"
            ;;
        9)
            AI_TYPE="xai"
            echo -e "     ${YELLOW}Tutorial:${NC} Get xAI keys at https://console.x.ai"
            echo -ne "     xAI Model [grok-beta]: "
            read XAI_MODEL
            [[ -z $XAI_MODEL ]] && XAI_MODEL="grok-beta"
            echo -ne "     xAI API Key: "
            read -s XAI_KEY
            echo ""
            print_info "Using xAI - $XAI_MODEL"
            ;;
        10)
            AI_TYPE="ollama"
            echo -e "     ${YELLOW}Tutorial:${NC} Install Ollama from https://ollama.ai"
            echo -ne "     Local Model [llama3.1:8b]: "
            read LOCAL_MODEL
            [[ -z $LOCAL_MODEL ]] && LOCAL_MODEL="llama3.1:8b"
            echo -ne "     Local Provider [ollama/lmstudio]: "
            read LOCAL_PROVIDER
            [[ -z $LOCAL_PROVIDER ]] && LOCAL_PROVIDER="ollama"
            print_info "Using Local AI - $LOCAL_MODEL via $LOCAL_PROVIDER"
            ;;
        *)
            AI_TYPE="standard"
            print_info "Defaulting to standard mode"
            ;;
    esac
    
    # AI Confidence Threshold
    echo ""
    echo -ne "     ${CYAN}Minimum confidence to trade${NC} [0.5-0.9]: "
    read CONF_THRESHOLD
    [[ -z $CONF_THRESHOLD ]] && CONF_THRESHOLD="0.65"

    echo ""
    echo -e "     ${BOLD}X (Twitter) Intelligence Sentinel:${NC}"
    echo -e "     ${YELLOW}Tutorial:${NC} Create an app at https://developer.x.com/en/portal/dashboard"
    echo -ne "     Enable X monitoring? [y/N]: "
    read ENABLE_X
    if [[ $ENABLE_X == "y" || $ENABLE_X == "Y" ]]; then
        echo -e "     ${DIM}Note: Requires 'Read and write' permissions for all 5 tokens${NC}"
        echo -ne "     X API Key: "
        read X_KEY
        echo -ne "     X API Secret: "
        read -s X_SECRET
        echo ""
        echo -ne "     X Bearer Token: "
        read -s X_BEARER
        echo ""
        echo -ne "     X Access Token: "
        read X_ACCESS
        echo -ne "     X Access Token Secret: "
        read -s X_ACCESS_SECRET
        echo ""
    fi
}

# === Step 5: Trading Configuration ===
configure_trading() {
    print_step "05" "Trading Parameters"
    echo ""
    
    echo -ne "     ${CYAN}Minimum profit threshold %${NC} [0.5]: "
    read MIN_PROFIT
    [[ -z $MIN_PROFIT ]] && MIN_PROFIT="0.5"
    
    echo -ne "     ${CYAN}Max position size (USD)${NC} [100]: "
    read MAX_POSITION
    [[ -z $MAX_POSITION ]] && MAX_POSITION="100"
    
    echo -ne "     ${CYAN}Minimum liquidity (USD)${NC} [5000]: "
    read MIN_LIQ
    [[ -z $MIN_LIQ ]] && MIN_LIQ="5000"
    
    echo -ne "     ${CYAN}Poll interval (seconds)${NC} [2]: "
    read POLL_INT
    [[ -z $POLL_INT ]] && POLL_INT="2"
    
    echo -ne "     ${CYAN}Risk per trade %${NC} [0.8]: "
    read RISK_PCT
    [[ -z $RISK_PCT ]] && RISK_PCT="0.8"
    
    echo ""
    echo -ne "     ${CYAN}Trading mode${NC} [dry-run/live]: "
    read TRADE_MODE
    [[ -z $TRADE_MODE ]] && TRADE_MODE="dry-run"
    [[ $TRADE_MODE == "live" ]] && DRY_RUN="false" || DRY_RUN="true"
}

# === Step 6: Generate .env ===
generate_env() {
    print_step "06" "Generating configuration"
    
    cat > .env << EOF
# ============================================
# POLYPULSE BOT v2.0 - CONFIGURATION
# ============================================

# WALLET SECURITY
PRIVATE_KEY=$PRIV_KEY
WALLET_ADDRESS=$WALLET_ADDR

# POLYMARKET L2 API
POLY_API_KEY=$POLY_KEY
POLY_API_SECRET=$POLY_SECRET
POLY_API_PASSPHRASE=$POLY_PASS

# NETWORK
POLYGON_RPC_URL=https://polygon-rpc.com
CHAIN_ID=137

# AI CONFIGURATION
ANALYZER_TYPE=$AI_TYPE
AI_CONFIDENCE_THRESHOLD=$CONF_THRESHOLD

# AI PROVIDER KEYS
GEMINI_API_KEY=$GEMINI_KEY
OPENAI_API_KEY=$OAI_KEY
ANTHROPIC_API_KEY=$ANT_KEY
GROQ_API_KEY=$GROQ_KEY
OPENROUTER_API_KEY=$OR_KEY
NVIDIA_API_KEY=$NV_KEY
HUGGINGFACE_API_KEY=$HF_KEY
XAI_API_KEY=$XAI_KEY

X_API_KEY=$X_KEY
X_API_SECRET=$X_SECRET
X_BEARER_TOKEN=$X_BEARER
X_ACCESS_TOKEN=$X_ACCESS
X_ACCESS_TOKEN_SECRET=$X_ACCESS_SECRET

# AI MODEL SELECTION
GOOGLE_CLOUD_PROJECT=$GCP_PROJECT
OPENAI_MODEL=${OAI_MODEL:-gpt-4o}
ANTHROPIC_MODEL=${ANT_MODEL:-claude-3-5-sonnet-20241022}
GROQ_MODEL=${GROQ_MODEL:-llama-3.1-70b-versatile}
OPENROUTER_MODEL=${OR_MODEL:-meta-llama/llama-3.1-405b-instruct}
NVIDIA_MODEL=${NV_MODEL:-nvidia/llama-3.1-nruro-70b-instruct}
XAI_MODEL=${XAI_MODEL:-grok-beta}
HUGGINGFACE_MODEL=${HF_MODEL:-meta-llama/Llama-3.1-70B-Instruct}
LOCAL_MODEL=${LOCAL_MODEL:-llama3.1:8b}

# TRADING PARAMETERS
MIN_PROFIT_THRESHOLD=0.0$MIN_PROFIT
MAX_POSITION_SIZE=$MAX_POSITION
MIN_LIQUIDITY_USD=$MIN_LIQ
POLL_INTERVAL_SECONDS=$POLL_INT
RISK_PER_TRADE_PCT=$RISK_PCT

# RISK MANAGEMENT
STOP_LOSS_PCT=5.0
POSITION_CAP_PCT=25.0
DAILY_DRAWDOWN_PCT=8.0
MONTHLY_DRAWDOWN_PCT=20.0

# STRATEGIES
ENABLE_FLASH_CRASH=true
ENABLE_MEAN_REVERSION=true
ENABLE_MOMENTUM=true
USE_SENTIMENT_FILTER=true

# DASHBOARD
DASHBOARD_PORT=8080
DASHBOARD_USERNAME=admin

# MODE
DRY_RUN=$DRY_RUN

# LOGGING
LOG_LEVEL=INFO
EOF

    print_success "Configuration saved to .env"
}

# === Final Summary ===
show_summary() {
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}          ${BOLD}SETUP COMPLETE - READY TO TRADE${NC}              ${GREEN}║${NC}"
    echo -e "${GREEN}╠══════════════════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║${NC}                                                      ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  ${WHITE}Configuration:${NC}                                  ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  • AI Provider: ${CYAN}$AI_TYPE${NC}"
    echo -e "${GREEN}║${NC}  • Trading Mode: ${YELLOW}${DRY_RUN^^}${NC}"
    echo -e "${GREEN}║${NC}  • Min Profit: ${GREEN}${MIN_PROFIT}%${NC}"
    echo -e "${GREEN}║${NC}  • Max Position: ${BLUE}\$${MAX_POSITION}${NC}"
    echo -e "${GREEN}║${NC}                                                      ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  ${WHITE}Next Steps:${NC}                                      ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                      ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  ${DIM}1. Review config:${NC} ${CYAN}cat .env${NC}"
    echo -e "${GREEN}║${NC}  ${DIM}2. Launch TUI:${NC}      ${CYAN}python -m rarb tui${NC}"
    echo -e "${GREEN}║${NC}  ${DIM}3. Run headless:${NC}  ${CYAN}python -m rarb run${NC}"
    echo -e "${GREEN}║${NC}  ${DIM}4. Scan markets:${NC}  ${CYAN}python -m rarb scan${NC}"
    echo -e "${GREEN}║${NC}                                                      ${GREEN}║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# === Main Execution ===
show_header
setup_environment
install_dependencies
configure_wallet
configure_ai
configure_trading
generate_env
show_summary

exit 0

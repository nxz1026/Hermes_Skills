#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Hermes Skills — Bootstrap Setup Script
# ─────────────────────────────────────────────────────────────────────────────
# Purpose  : Idempotent bootstrap for the Hermes Skills workspace.
# Usage    : ./setup.sh [--execute] [--step <N>] [--verbose]
# Safety   : Default = dry-run (print what WOULD happen).
#            --execute  = actually apply changes.
#            --step <N> = run only step 1-6 (see STEP_* functions).
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail
IFS=$'\n\t'

# ── Globals ──────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HERMES_ROOT="${HERMES_ROOT:-$HOME/.hermes}"
LOG_FILE="$PROJECT_ROOT/setup_$(date +%Y%m%d_%H%M%S).log"

DRY_RUN=1          # 1 = dry-run, 0 = execute
VERBOSE=0
RUN_STEP=0         # 0 = all steps, 1-6 = specific step
CHANGES=()         # track what would be done

# ── Color helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log()   { echo -e "${CYAN}[setup]${NC} $*" | tee -a "$LOG_FILE"; }
ok()    { echo -e "${GREEN}[  OK ]${NC} $*" | tee -a "$LOG_FILE"; }
warn()  { echo -e "${YELLOW}[WARN ]${NC} $*" | tee -a "$LOG_FILE"; }
err()   { echo -e "${RED}[FAIL ]${NC} $*" | tee -a "$LOG_FILE"; }
diff()  { echo -e "${YELLOW}[DIFF]${NC} $*" | tee -a "$LOG_FILE"; }

# ── Usage ────────────────────────────────────────────────────────────────────
usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Bootstrap the Hermes Skills workspace.  Safe by default — prints actions
without executing them.  Use --execute to apply changes.

Options:
  --execute    Actually apply changes (default: dry-run)
  --step N     Run only step N (1=check, 2=providers, 3=cron,
               4=scripts, 5=iptables, 6=mem0, 7=verify)
  --verbose    Print extra detail
  --help       Show this help

Examples:
  ./setup.sh                  # dry-run everything
  ./setup.sh --execute        # apply everything
  ./setup.sh --step 2         # dry-run step 2 only
  ./setup.sh --execute --step 5  # apply iptables config
EOF
    exit 0
}

# ── Parse args ───────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --execute) DRY_RUN=0; shift ;;
        --step)    RUN_STEP="$2"; shift 2 ;;
        --verbose) VERBOSE=1; shift ;;
        --help|-h) usage ;;
        *) warn "Unknown arg: $1"; usage ;;
    esac
done

# ── Utility: run or dry-run ──────────────────────────────────────────────────
run() {
    local desc="$1"; shift
    if [[ $DRY_RUN -eq 1 ]]; then
        diff "WOULD RUN: $desc"
        CHANGES+=("$desc")
    else
        log "RUNNING: $desc"
        eval "$@" 2>&1 | tee -a "$LOG_FILE"
    fi
}

# ── Utility: write file or print diff ────────────────────────────────────────
write_file() {
    local path="$1" content="$2"
    if [[ -f "$path" ]]; then
        local existing
        existing="$(cat "$path")"
        if [[ "$existing" == "$content" ]]; then
            ok "File unchanged: $path"
            return 0
        fi
        if [[ $DRY_RUN -eq 1 ]]; then
            diff "WOULD UPDATE: $path"
            diff "--- old ($path)"
            echo "$existing" | head -5 | sed 's/^/  /' | tee -a "$LOG_FILE"
            diff "--- new (proposed)"
            echo "$content"   | head -5 | sed 's/^/  /' | tee -a "$LOG_FILE"
            CHANGES+=("Update $path")
        else
            log "Updating: $path"
            cp "$path" "${path}.bak.$(date +%s)"
            printf '%s\n' "$content" > "$path"
        fi
    else
        if [[ $DRY_RUN -eq 1 ]]; then
            diff "WOULD CREATE: $path"
            CHANGES+=("Create $path")
        else
            log "Creating: $path"
            mkdir -p "$(dirname "$path")"
            printf '%s\n' "$content" > "$path"
        fi
    fi
}

# ── Utility: ensure directory exists ─────────────────────────────────────────
ensure_dir() {
    local path="$1"
    if [[ ! -d "$path" ]]; then
        run "Create directory: $path" "mkdir -p '$path'"
    else
        ok "Directory exists: $path"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Pre-flight checks
# ═══════════════════════════════════════════════════════════════════════════════
step_check() {
    log "${BOLD}━━━ Step 1: Pre-flight checks ━━━${NC}"

    local pass=0 fail=0

    # 1.1 Bash version >= 4.0
    if ((BASH_VERSINFO[0] >= 4)); then
        ok "Bash version: ${BASH_VERSION}"
        ((pass++)) || true
    else
        err "Bash >= 4.0 required, got ${BASH_VERSION}"
        ((fail++)) || true
    fi

    # 1.2 Hermes CLI available
    if command -v hermes &>/dev/null; then
        ok "hermes CLI: $(hermes --version 2>/dev/null || echo 'version unknown, but present')"
        ((pass++)) || true
    else
        err "hermes CLI not found in PATH"
        ((fail++)) || true
    fi

    # 1.3 Python3 >= 3.10
    if command -v python3 &>/dev/null; then
        local pyver
        pyver="$(python3 -c 'import sys; print(f"{sys.version_info.major}{sys.version_info.minor}")')"
        if ((pyver >= 310)); then
            ok "Python: $(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
            ((pass++)) || true
        else
            err "Python >= 3.10 required, got ${pyver}"
            ((fail++)) || true
        fi
    else
        err "python3 not found"
        ((fail++)) || true
    fi

    # 1.4 PyYAML (needed by helpers)
    if python3 -c "import yaml" 2>/dev/null; then
        ok "PyYAML available"
        ((pass++)) || true
    else
        warn "PyYAML not installed — some features may fail"
        ((fail++)) || true
    fi

    # 1.5 Hermes root directories
    for d in "$HERMES_ROOT" "$HERMES_ROOT/skills" "$HERMES_ROOT/scripts" "$HERMES_ROOT/cron"; do
        if [[ -d "$d" ]]; then
            ok "Directory: $d"
            ((pass++)) || true
        else
            warn "Missing directory: $d (will create if needed)"
        fi
    done

    # 1.6 .env file (must exist but we never read its content)
    if [[ -f "$HERMES_ROOT/.env" ]]; then
        ok ".env file exists (content not read — credential store)"
        ((pass++)) || true
    else
        err ".env file not found at $HERMES_ROOT/.env"
        ((fail++)) || true
    fi

    # 1.7 config.yaml
    if [[ -f "$HERMES_ROOT/config.yaml" ]]; then
        ok "config.yaml exists"
        ((pass++)) || true
    else
        err "config.yaml not found at $HERMES_ROOT/config.yaml"
        ((fail++)) || true
    fi

    # 1.8 Git installed
    if command -v git &>/dev/null; then
        ok "git: $(git --version | awk '{print $3}')"
        ((pass++)) || true
    else
        warn "git not found"
    fi

    # 1.9 iptables available (optional — may not work in containers)
    if command -v iptables &>/dev/null; then
        ok "iptables available"
        ((pass++)) || true
    else
        warn "iptables not found — step 5 will be skipped"
    fi

    # 1.10 Project directories
    for d in "$PROJECT_ROOT/references" "$PROJECT_ROOT/scripts"; do
        if [[ -d "$d" ]]; then
            ok "Project dir: $d"
            ((pass++)) || true
        else
            warn "Project dir missing: $d"
        fi
    done

    log "Checks: ${pass} passed, ${fail} failed"
    if [[ $fail -gt 0 ]]; then
        err "Pre-flight checks failed. Fix issues above before proceeding."
        return 1
    fi
    ok "All critical checks passed."
}

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Configure providers (LongCat api_mode=openai)
# ═══════════════════════════════════════════════════════════════════════════════
step_providers() {
    log "${BOLD}━━━ Step 2: Configure providers ━━━${NC}"

    # We do NOT read or write API keys. The .env file is the sole source.
    # We verify the provider structure exists in config.yaml.

    local cfg="$HERMES_ROOT/config.yaml"

    if [[ ! -f "$cfg" ]]; then
        err "config.yaml not found — skipping provider setup"
        return 1
    fi

    # 2.1 Verify LongCat provider exists in custom_providers
    if grep -q "Api.longcat.chat" "$cfg" 2>/dev/null; then
        ok "LongCat provider (Api.longcat.chat) found in config.yaml"
    else
        warn "Api.longcat.chat provider not found in config.yaml — ensure it is configured"
    fi

    # 2.2 Verify api_mode=openai for LongCat
    if grep -A5 "Api.longcat.chat" "$cfg" 2>/dev/null | grep -q "api_mode: openai"; then
        ok "LongCat api_mode=openai confirmed"
    else
        warn "Could not confirm api_mode=openai for LongCat — check config.yaml"
    fi

    # 2.3 Verify base_url
    if grep -A5 "Api.longcat.chat" "$cfg" 2>/dev/null | grep -q "api.longcat.chat"; then
        ok "LongCat base_url points to api.longcat.chat"
    else
        warn "LongCat base_url may be misconfigured"
    fi

    # 2.4 Verify .env has required keys (check key names only, not values)
    local required_keys=(
        "NVIDIA_API_KEY"
        "XUNFEI_API_KEY"
        "XF_YUN_BASE_URL"
    )
    for key in "${required_keys[@]}"; do
        if grep -q "^${key}=" "$HERMES_ROOT/.env" 2>/dev/null; then
            ok ".env has key: $key"
        else
            warn ".env missing key: $key (may be needed for auxiliary providers)"
        fi
    done

    # 2.5 Verify main model config
    if grep -q "default: LongCat-2.0-Preview" "$cfg" 2>/dev/null; then
        ok "Main model: LongCat-2.0-Preview"
    else
        warn "Main model may not be LongCat-2.0-Preview"
    fi

    ok "Provider configuration verified."
}

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Create 8 cron jobs
# ═══════════════════════════════════════════════════════════════════════════════
step_cron() {
    log "${BOLD}━━━ Step 3: Create cron jobs ━━━${NC}"

    if ! command -v hermes &>/dev/null; then
        err "hermes CLI not available — cannot create cron jobs"
        return 1
    fi

    # Define all 8 cron jobs
    # Format: "name|schedule|provider|model|skill|toolsets|prompt_override"
    local jobs=(
        "📰 每日晨报|10 23 * * *|custom:Api.longcat.chat|LongCat-2.0-Preview|hermes-daily-morning-report|web,terminal,file|"
        "日志扫描|20 17 * * *|custom:Api.longcat.chat|LongCat-2.0-Preview|log-daily-scan|terminal,file|"
        "🛌 SkillOpt-Sleep weekly|10 21 * * 0|custom:Api.longcat.chat|LongCat-2.0-Preview|skillopt-integration|terminal,file|"
        "⚽ 世界杯预测(一体化)|30 2 * * *|custom:Api.longcat.chat|LongCat-2.0-Preview|world-cup-predict|web,terminal,file|"
        "🎯 接活雷达 + 成都招聘（晚间版）|30 10 * * *|custom:Api.longcat.chat|LongCat-2.0-Preview|freelance-radar||"
        "📚 IMA知识库更新|10 16 * * *|custom||hermes-knowledge-update|web,terminal,file|"
        "📊 模型健康报告|0 18 * * *|||terminal|"
        "📊 模型标杆测试|0 22 * * *|||terminal|"
    )

    local toolset_flag=""
    local model_flag=""
    local deliver_flag="--deliver feishu"

    for jobspec in "${jobs[@]}"; do
        IFS='|' read -r name schedule provider model skill toolsets prompt_override <<< "$jobspec"

        # Check if job already exists (by name)
        if hermes cron list 2>/dev/null | grep -qF "$name"; then
            ok "Cron already exists: $name"
            continue
        fi

        # Build command
        local cmd="hermes cron create"
        local safe_name="${name//\'/\'\"\'\"\'}"
        cmd+=" --name '$safe_name'"
        cmd+=" $schedule"

        if [[ -n "$model" ]]; then
            cmd+=" --provider '$provider'"
        fi

        if [[ -n "$skill" ]]; then
            cmd+=" --skill '$skill'"
        fi

        cmd+=" $deliver_flag"

        # Script-based jobs (model health, model benchmark)
        case "$name" in
            *"模型健康报告"*)
                cmd+=" --script $HERMES_ROOT/scripts/model_health.py --no-agent"
                ;;
            *"模型标杆测试"*)
                cmd+=" --script $HERMES_ROOT/scripts/model_benchmark.py --no-agent"
                ;;
            *"IMA知识库更新"*)
                # No skill flag — uses prompt with skill reference
                ;;
        esac

        # Add toolset restrictions if specified
        if [[ -n "$toolsets" ]]; then
            # hermes cron create doesn't have --toolsets flag directly
            # Toolsets are set via edit after creation
            :
        fi

        run "Create cron: $name ($schedule)" "$cmd"
    done

    # Note: toolset restrictions need to be set via hermes cron edit
    # This is a known limitation — we document it
    if [[ $DRY_RUN -eq 0 ]]; then
        log "Note: Toolset restrictions for cron jobs may need manual adjustment."
        log "      Use 'hermes cron edit <id> --toolsets <list>' to set them."
    fi

    ok "Cron jobs processed."
}

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Deploy scripts
# ═══════════════════════════════════════════════════════════════════════════════
step_scripts() {
    log "${BOLD}━━━ Step 4: Deploy scripts ━━━${NC}"

    local src_dir="$PROJECT_ROOT/scripts"
    local dst_dir="$HERMES_ROOT/scripts"

    if [[ ! -d "$src_dir" ]]; then
        err "Source scripts directory not found: $src_dir"
        return 1
    fi

    ensure_dir "$dst_dir"

    # List of scripts to deploy (relative to project scripts/)
    local scripts=(
        "setup.sh"
    )

    for script in "${scripts[@]}"; do
        local src="$src_dir/$script"
        local dst="$dst_dir/$script"

        if [[ ! -f "$src" ]]; then
            warn "Source script not found: $src"
            continue
        fi

        if [[ -f "$dst" ]]; then
            # Compare
            if diff -q "$src" "$dst" &>/dev/null; then
                ok "Script unchanged: $script"
            else
                run "Update script: $script" "cp '$src' '$dst' && chmod +x '$dst'"
            fi
        else
            run "Deploy script: $script" "cp '$src' '$dst' && chmod +x '$dst'"
        fi
    done

    # Verify critical scripts exist in target
    local critical_scripts=(
        "model_health.py"
        "model_benchmark.py"
        "Log_daily_status.py"
        "predict_wc.py"
        "backup.sh"
        "token_stats.py"
    )

    for script in "${critical_scripts[@]}"; do
        if [[ -f "$dst_dir/$script" ]]; then
            ok "Critical script present: $script"
        else
            warn "Critical script missing from $dst_dir: $script"
        fi
    done

    ok "Scripts deployment check complete."
}

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 5 — Configure iptables
# ═══════════════════════════════════════════════════════════════════════════════
step_iptables() {
    log "${BOLD}━━━ Step 5: Configure iptables ━━━${NC}"

    if ! command -v iptables &>/dev/null; then
        warn "iptables not available — skipping firewall configuration"
        return 0
    fi

    # Detect current state
    local current_docker_rules
    current_docker_rules="$(iptables -L DOCKER -n 2>/dev/null || echo 'NOT_FOUND')"

    # 5.1 Ensure DOCKER chain defaults to DROP
    if echo "$current_docker_rules" | grep -q "DROP all"; then
        ok "DOCKER chain already defaults to DROP"
    else
        run "Set DOCKER chain policy to DROP" "iptables -P DOCKER DROP"
    fi

    # 5.2 Ensure DOCKER-CT allows related/established
    local docker_ct
    docker_ct="$(iptables -L DOCKER-CT -n 2>/dev/null || echo 'NOT_FOUND')"
    if echo "$docker_ct" | grep -q "RELATED,ESTABLISHED"; then
        ok "DOCKER-CT allows RELATED,ESTABLISHED"
    else
        run "Allow RELATED,ESTABLISHED in DOCKER-CT" \
            "iptables -A DOCKER-CT -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT"
    fi

    # 5.3 Ensure FORWARD chain defaults to DROP
    local forward_policy
    forward_policy="$(iptables -L FORWARD -n 2>/dev/null | head -1 | grep -o 'DROP\|ACCEPT' || echo 'UNKNOWN')"
    if [[ "$forward_policy" == "DROP" ]]; then
        ok "FORWARD chain defaults to DROP"
    else
        run "Set FORWARD chain policy to DROP" "iptables -P FORWARD DROP"
    fi

    # 5.4 Ensure SSH rate-limiting exists
    local has_ssh_rate=0
    if iptables -L INPUT -n 2>/dev/null | grep -q "recent: SET"; then
        has_ssh_rate=1
        ok "SSH rate-limiting already configured"
    else
        # Add SSH rate-limit rule
        run "Add SSH rate-limit (60s/4 connections)" \
            "iptables -A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW -m recent --set --name ssh_limiter"
        run "Add SSH rate-limit DROP rule" \
            "iptables -A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW -m recent --update --seconds 60 --hitcount 4 --name ssh_limiter -j DROP"
    fi

    # 5.5 Block known malicious IPs (from reference)
    local blocked_ips=(
        "87.251.64.145"
        "81.90.28.163"
        "45.148.10.183"
        "47.236.245.255"
        "185.204.171.193"
        "61.75.245.101"
        "59.153.245.232"
        "87.251.64.144"
    )

    for ip in "${blocked_ips[@]}"; do
        if iptables -L INPUT -n 2>/dev/null | grep -qF "$ip"; then
            ok "Already blocked: $ip"
        else
            run "Block IP: $ip" "iptables -A INPUT -s $ip -j DROP"
        fi
    done

    # 5.6 Docker isolation rules
    if ! iptables -L DOCKER-FORWARD -n 2>/dev/null | grep -q "DOCKER-CT"; then
        run "Ensure DOCKER-FORWARD chain exists" \
            "iptables -N DOCKER-FORWARD 2>/dev/null; iptables -A FORWARD -j DOCKER-FORWARD"
    else
        ok "DOCKER-FORWARD chain configured"
    fi

    # 5.7 Save rules (if iptables-persistent or similar is available)
    if command -v iptables-save &>/dev/null; then
        run "Save iptables rules" "iptables-save > /etc/iptables/rules.v4 2>/dev/null || true"
    elif command -v netfilter-persistent &>/dev/null; then
        run "Persist iptables rules" "netfilter-persistent save"
    else
        warn "No iptables persistence mechanism found — rules will not survive reboot"
        warn "Install iptables-persistent: apt-get install iptables-persistent"
    fi

    ok "IPTables configuration processed."
}

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 6 — Configure mem0
# ═══════════════════════════════════════════════════════════════════════════════
step_mem0() {
    log "${BOLD}━━━ Step 6: Configure mem0 ━━━${NC}"

    local mem0_dir="$HERMES_ROOT/mem0"
    local mem0_cfg="$mem0_dir/config.yaml"

    # 6.1 Ensure mem0 directory exists
    ensure_dir "$mem0_dir"
    ensure_dir "$mem0_dir/qdrant"
    ensure_dir "$HOME/.mem0/qdrant"

    # 6.2 Check if mem0 Python package is installed
    if python3 -c "import mem0ai" 2>/dev/null; then
        ok "mem0ai Python package installed"
    else
        run "Install mem0ai Python package" "pip3 install mem0ai"
    fi

    # 6.3 Check if sentence-transformers is available
    if python3 -c "import sentence_transformers" 2>/dev/null; then
        ok "sentence-transformers available"
    else
        run "Install sentence-transformers" "pip3 install sentence-transformers"
    fi

    # 6.4 Check if qdrant_client is available
    if python3 -c "import qdrant_client" 2>/dev/null; then
        ok "qdrant_client available"
    else
        run "Install qdrant_client" "pip3 install qdrant-client"
    fi

    # 6.5 Verify mem0 config.yaml structure (don't overwrite if exists)
    if [[ -f "$mem0_cfg" ]]; then
        # Check key fields
        local checks=("llm:" "embedder:" "vector_store:" "history_store:" "defaults:")
        for check in "${checks[@]}"; do
            if grep -q "^$check" "$mem0_cfg"; then
                ok "mem0 config has section: $check"
            else
                warn "mem0 config missing section: $check"
            fi
        done

        # Verify LLM config uses env var for API key
        if grep -q "\${NVIDIA_API_KEY}" "$mem0_cfg"; then
            ok "mem0 LLM uses NVIDIA_API_KEY from env (not hardcoded)"
        else
            warn "mem0 LLM API key may be hardcoded — should use \${NVIDIA_API_KEY}"
        fi

        # Verify embedder config
        if grep -q "all-MiniLM-L6-v2" "$mem0_cfg"; then
            ok "mem0 embedder: all-MiniLM-L6-v2"
        else
            warn "mem0 embedder model unexpected"
        fi

        # Verify vector store
        if grep -q "qdrant" "$mem0_cfg"; then
            ok "mem0 vector store: qdrant"
        else
            warn "mem0 vector store may not be qdrant"
        fi

        ok "mem0 config.yaml exists — not overwriting"
    else
        warn "mem0 config.yaml not found at $mem0_cfg"
        warn "Create it with: provider=openai, model from NVIDIA NIM, api_key from env"
    fi

    # 6.6 Verify user_id
    if [[ -f "$mem0_cfg" ]]; then
        if grep -q "user_id:" "$mem0_cfg"; then
            local uid
            uid="$(grep "user_id:" "$mem0_cfg" | head -1 | awk '{print $2}')"
            ok "mem0 default user_id: $uid"
        else
            warn "mem0 config missing user_id"
        fi
    fi

    # 6.7 Verify wrapper.py exists
    if [[ -f "$mem0_dir/wrapper.py" ]]; then
        ok "mem0 wrapper.py exists"
    else
        warn "mem0 wrapper.py not found at $mem0_dir/wrapper.py"
    fi

    # 6.8 Check Qdrant data directory
    if [[ -d "$HOME/.mem0/qdrant" ]]; then
        ok "Qdrant data directory exists: $HOME/.mem0/qdrant"
    else
        run "Create Qdrant data directory" "mkdir -p $HOME/.mem0/qdrant"
    fi

    # 6.9 Verify sqlite3 for history store
    if [[ -f "$HOME/.mem0/history.db" ]]; then
        ok "History store exists: $HOME/.mem0/history.db"
    else
        run "Create history.db" "touch $HOME/.mem0/history.db"
    fi

    ok "mem0 configuration processed."
}

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 7 — Verify
# ═══════════════════════════════════════════════════════════════════════════════
step_verify() {
    log "${BOLD}━━━ Step 7: Verification ━━━${NC}"

    local pass=0 fail=0

    # 7.1 Verify hermes cron list returns 8 jobs
    local cron_count
    cron_count="$(hermes cron list 2>/dev/null | grep -c '\[' || echo 0)"
    if [[ $cron_count -ge 8 ]]; then
        ok "Cron jobs: $cron_count found (expected >= 8)"
        ((pass++)) || true
    else
        err "Cron jobs: $cron_count found (expected >= 8)"
        ((fail++)) || true
    fi

    # 7.2 Verify config.yaml has LongCat provider
    if grep -q "Api.longcat.chat" "$HERMES_ROOT/config.yaml" 2>/dev/null; then
        ok "LongCat provider in config.yaml"
        ((pass++)) || true
    else
        err "LongCat provider not in config.yaml"
        ((fail++)) || true
    fi

    # 7.3 Verify api_mode=openai
    if grep -A10 "Api.longcat.chat" "$HERMES_ROOT/config.yaml" 2>/dev/null | grep -q "api_mode: openai"; then
        ok "LongCat api_mode=openai"
        ((pass++)) || true
    else
        warn "LongCat api_mode not confirmed as openai"
        ((fail++)) || true
    fi

    # 7.4 Verify .env has API keys (names only)
    for key in "NVIDIA_API_KEY" "XUNFEI_API_KEY"; do
        if grep -q "^${key}=" "$HERMES_ROOT/.env" 2>/dev/null; then
            ok ".env has: $key"
            ((pass++)) || true
        else
            warn ".env missing: $key"
            ((fail++)) || true
        fi
    done

    # 7.5 Verify scripts exist
    for script in "model_health.py" "model_benchmark.py" "backup.sh"; do
        if [[ -f "$HERMES_ROOT/scripts/$script" ]]; then
            ok "Script: $script"
            ((pass++)) || true
        else
            err "Missing script: $script"
            ((fail++)) || true
        fi
    done

    # 7.6 Verify mem0 config
    if [[ -f "$HERMES_ROOT/mem0/config.yaml" ]]; then
        ok "mem0 config.yaml exists"
        ((pass++)) || true
        if grep -q "qdrant" "$HERMES_ROOT/mem0/config.yaml"; then
            ok "mem0 uses qdrant"
            ((pass++)) || true
        fi
    else
        warn "mem0 config.yaml missing"
        ((fail++)) || true
    fi

    # 7.7 Verify iptables DOCKER chain
    if iptables -L DOCKER -n 2>/dev/null | grep -q "DROP all"; then
        ok "iptables DOCKER chain defaults to DROP"
        ((pass++)) || true
    else
        warn "iptables DOCKER chain may not default to DROP"
        ((fail++)) || true
    fi

    # 7.8 Verify Qdrant data dir
    if [[ -d "$HOME/.mem0/qdrant" ]]; then
        ok "Qdrant data dir exists"
        ((pass++)) || true
    else
        warn "Qdrant data dir missing"
        ((fail++)) || true
    fi

    # 7.9 Verify Python dependencies
    for pkg in "yaml" "mem0ai"; do
        if python3 -c "import $pkg" 2>/dev/null; then
            ok "Python package: $pkg"
            ((pass++)) || true
        else
            warn "Python package missing: $pkg"
            ((fail++)) || true
        fi
    done

    log ""
    log "═══════════════════════════════════════════"
    log "Verification: ${pass} passed, ${fail} failed"
    log "═══════════════════════════════════════════"

    if [[ $fail -gt 0 ]]; then
        warn "Some verifications failed — review output above"
        return 1
    fi
    ok "All verifications passed!"
}

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
main() {
    log ""
    log "${BOLD}╔══════════════════════════════════════════════════════════╗${NC}"
    log "${BOLD}║       Hermes Skills — Bootstrap Setup Script            ║${NC}"
    log "${BOLD}╚══════════════════════════════════════════════════════════╝${NC}"
    log ""
    log "Mode: $(if [[ $DRY_RUN -eq 1 ]]; then echo -e "${YELLOW}DRY-RUN${NC}"; else echo -e "${RED}EXECUTE${NC}"; fi)"
    log "Step: $(if [[ $RUN_STEP -eq 0 ]]; then echo 'All'; else echo "$RUN_STEP"; fi)"
    log "Log : $LOG_FILE"
    log ""

    # Trap to print summary on exit
    trap 'print_summary' EXIT

    if [[ $RUN_STEP -eq 0 ]] || [[ $RUN_STEP -eq 1 ]]; then step_check;   fi
    if [[ $RUN_STEP -eq 0 ]] || [[ $RUN_STEP -eq 2 ]]; then step_providers; fi
    if [[ $RUN_STEP -eq 0 ]] || [[ $RUN_STEP -eq 3 ]]; then step_cron;    fi
    if [[ $RUN_STEP -eq 0 ]] || [[ $RUN_STEP -eq 4 ]]; then step_scripts;  fi
    if [[ $RUN_STEP -eq 0 ]] || [[ $RUN_STEP -eq 5 ]]; then step_iptables; fi
    if [[ $RUN_STEP -eq 0 ]] || [[ $RUN_STEP -eq 6 ]]; then step_mem0;     fi
    if [[ $RUN_STEP -eq 0 ]] || [[ $RUN_STEP -eq 7 ]]; then step_verify;  fi

    log ""
    log "${BOLD}━━━ Setup complete ━━━${NC}"
}

print_summary() {
    local exit_code=$?
    log ""
    if [[ $DRY_RUN -eq 1 ]]; then
        log "${YELLOW}━━━ DRY-RUN SUMMARY ━━━${NC}"
        log "No changes were made. Run with --execute to apply."
        if [[ ${#CHANGES[@]} -gt 0 ]]; then
            log ""
            log "Actions that would be taken:"
            for c in "${CHANGES[@]}"; do
                log "  • $c"
            done
        fi
    else
        log "${GREEN}━━━ EXECUTION COMPLETE ━━━${NC}"
    fi
    log "Full log: $LOG_FILE"
    exit $exit_code
}

main

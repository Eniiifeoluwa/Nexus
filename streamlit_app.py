"""
Autonomous Multi-Agent AI System — Streamlit Frontend
──────────────────────────────────────────────────────
Full UI for submitting tasks, watching agents run in real-time,
reviewing reports, and inspecting metrics.

Deploy free on Streamlit Community Cloud:
  https://streamlit.io/cloud
"""

import json
import time
from datetime import datetime
from pathlib import Path

import streamlit as st
import requests

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Autonomous Agent System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

.stApp {
    background: #080c14;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #0d1520 !important;
    border-right: 1px solid #1e2d42;
}

/* Main header */
.main-title {
    font-family: 'Space Mono', monospace;
    font-size: 1.6rem;
    font-weight: 700;
    color: #e2f0ff;
    letter-spacing: -0.02em;
    margin-bottom: 0;
    line-height: 1.2;
}
.main-subtitle {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.85rem;
    color: #4a6fa5;
    margin-top: 4px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

/* Agent step cards */
.agent-card {
    background: #0d1520;
    border: 1px solid #1e2d42;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 14px;
    transition: border-color 0.3s;
}
.agent-card.active {
    border-color: #2a7aff;
    background: #0b1830;
    box-shadow: 0 0 20px rgba(42,122,255,0.12);
}
.agent-card.done {
    border-color: #1a4a2e;
    background: #0b1a12;
}
.agent-card.pending {
    opacity: 0.45;
}

.agent-dot {
    width: 10px; height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
}
.dot-done   { background: #2dbd6e; }
.dot-active { background: #2a7aff; box-shadow: 0 0 8px #2a7aff; animation: pulse 1.2s ease-in-out infinite; }
.dot-pending { background: #1e2d42; }

@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.8); }
}

.agent-name {
    font-family: 'Space Mono', monospace;
    font-size: 0.82rem;
    color: #c8deff;
    font-weight: 700;
}
.agent-desc {
    font-size: 0.75rem;
    color: #4a6fa5;
    margin-top: 1px;
}

/* Metric cards */
.metric-box {
    background: #0d1520;
    border: 1px solid #1e2d42;
    border-radius: 10px;
    padding: 18px 20px;
    text-align: center;
}
.metric-val {
    font-family: 'Space Mono', monospace;
    font-size: 2rem;
    font-weight: 700;
    color: #2a7aff;
    line-height: 1;
}
.metric-label {
    font-size: 0.72rem;
    color: #4a6fa5;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 6px;
}

/* Status pill */
.pill {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    font-family: 'Space Mono', monospace;
    letter-spacing: 0.04em;
}
.pill-running  { background: #0b2040; color: #2a7aff; border: 1px solid #1a4070; }
.pill-complete { background: #0b2015; color: #2dbd6e; border: 1px solid #1a4a2e; }
.pill-failed   { background: #2a0b0b; color: #ff4a4a; border: 1px solid #4a1a1a; }
.pill-awaiting { background: #2a1f0b; color: #ffb32a; border: 1px solid #4a3a1a; }

/* Report container */
.report-box {
    background: #0a0f1a;
    border: 1px solid #1e2d42;
    border-radius: 12px;
    padding: 28px 32px;
    font-family: 'DM Sans', sans-serif;
    color: #c8deff;
    line-height: 1.7;
    max-height: 520px;
    overflow-y: auto;
}

/* Submit button */
div[data-testid="stButton"] button {
    background: linear-gradient(135deg, #1a4aff, #0a2adf) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Space Mono', monospace !important;
    font-weight: 700 !important;
    letter-spacing: 0.04em !important;
    padding: 0.6rem 2rem !important;
    font-size: 0.85rem !important;
    transition: all 0.2s !important;
}
div[data-testid="stButton"] button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 20px rgba(42, 122, 255, 0.35) !important;
}

/* Text area */
textarea {
    background: #0d1520 !important;
    color: #c8deff !important;
    border: 1px solid #1e2d42 !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* Code blocks */
code, pre {
    font-family: 'Space Mono', monospace !important;
    font-size: 0.78rem !important;
    background: #080c14 !important;
    color: #7ab8ff !important;
}

/* Dividers */
hr { border-color: #1e2d42 !important; }

/* Tab styling */
button[data-baseweb="tab"] {
    font-family: 'Space Mono', monospace !important;
    font-size: 0.78rem !important;
    color: #4a6fa5 !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #2a7aff !important;
}

/* Progress bar */
div[data-testid="stProgress"] > div > div {
    background: linear-gradient(90deg, #1a4aff, #2dbd6e) !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #080c14; }
::-webkit-scrollbar-thumb { background: #1e2d42; border-radius: 2px; }

.stTextArea label, .stTextInput label, .stSelectbox label {
    color: #4a6fa5 !important;
    font-size: 0.78rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}

.block-container { padding-top: 2rem !important; }

.stAlert { border-radius: 8px !important; }

/* Hide streamlit branding */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
AGENT_STEPS = [
    ("PlannerAgent",    "📐", "Decomposes task into subtasks"),
    ("ResearchAgent",   "🔍", "Web search + vector memory"),
    ("CoderAgent",      "💻", "Generates Python code"),
    ("ExecutorAgent",   "⚙️",  "Runs code in sandbox"),
    ("CriticAgent",     "🔬", "Evaluates output quality"),
    ("ReporterAgent",   "📄", "Compiles final report"),
]

DEFAULT_TASK = (
    "Research global electric vehicle adoption trends from 2018–2024. "
    "Generate a synthetic dataset with regional EV sales, market share, and "
    "charging infrastructure. Perform statistical analysis, create visualisations "
    "(line charts, bar charts, heatmaps), identify the top 3 growth markets, "
    "and produce a comprehensive structured report with Python code and insights."
)

EXAMPLE_TASKS = {
    "🚗 EV Market Analysis": DEFAULT_TASK,
    "☀️ Renewable Energy Trends": (
        "Analyse global renewable energy capacity growth 2010–2023. Generate "
        "synthetic solar/wind/hydro datasets by region. Run EDA, compute CAGR, "
        "identify leading countries, create multi-panel visualisations, and write "
        "a structured report with forecasts and policy recommendations."
    ),
    "📈 Stock Market Patterns": (
        "Analyse stock market volatility patterns for tech sector 2020–2024. "
        "Generate synthetic OHLCV data for 5 companies. Calculate rolling volatility, "
        "Sharpe ratios, drawdowns, correlations. Create candlestick-style charts and "
        "a risk analysis report with actionable insights."
    ),
    "🏥 Healthcare Data Analysis": (
        "Analyse patient outcome data across hospital departments. Generate synthetic "
        "dataset with demographics, diagnoses, treatment costs and recovery times. "
        "Run survival analysis, identify cost drivers, create heatmaps and scatter plots, "
        "and produce a healthcare insights report with recommendations."
    ),
}

# ── Session state ──────────────────────────────────────────────────────────────
for key, default in {
    "task_id": None,
    "status": None,
    "result": None,
    "polling": False,
    "log": [],
    "api_host": "http://localhost:8000",
    "last_step": "",
    "start_time": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ── API helpers ────────────────────────────────────────────────────────────────
def api_get(path: str) -> dict | None:
    try:
        r = requests.get(f"{st.session_state.api_host}{path}", timeout=8)
        if r.ok:
            return r.json()
    except Exception as e:
        st.session_state.log.append(f"⚠ API error: {e}")
    return None


def api_post(path: str, data: dict) -> dict | None:
    try:
        r = requests.post(
            f"{st.session_state.api_host}{path}",
            json=data, timeout=10
        )
        if r.ok:
            return r.json()
        st.error(f"API error {r.status_code}: {r.text[:200]}")
    except Exception as e:
        st.error(f"Cannot reach API at {st.session_state.api_host}: {e}")
    return None


def check_health() -> bool:
    h = api_get("/health")
    return h is not None and h.get("status") == "healthy"


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='padding: 8px 0 20px'>
        <div style='font-family: Space Mono, monospace; font-size: 1.1rem; color: #e2f0ff; font-weight: 700;'>
            🤖 AMAS
        </div>
        <div style='font-size: 0.72rem; color: #4a6fa5; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 2px;'>
            Autonomous Multi-Agent System
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("<div style='font-size:0.72rem;color:#4a6fa5;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px'>API Config</div>", unsafe_allow_html=True)
    host = st.text_input("API Host", value=st.session_state.api_host, label_visibility="collapsed")
    st.session_state.api_host = host.rstrip("/")

    healthy = check_health()
    if healthy:
        st.markdown("<div style='color:#2dbd6e;font-size:0.8rem;font-family:Space Mono,monospace'>● API Online</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='color:#ff4a4a;font-size:0.8rem;font-family:Space Mono,monospace'>● API Offline</div>", unsafe_allow_html=True)
        st.caption("Start the API: `uvicorn api.main:app --port 8000`")

    st.markdown("---")

    # System metrics
    st.markdown("<div style='font-size:0.72rem;color:#4a6fa5;text-transform:uppercase;letter-spacing:.08em;margin-bottom:12px'>System Metrics</div>", unsafe_allow_html=True)
    metrics = api_get("/metrics")
    if metrics:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""<div class='metric-box'>
                <div class='metric-val'>{metrics.get('total_tasks', 0)}</div>
                <div class='metric-label'>Tasks</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            rate = metrics.get('task_success_rate', 0)
            st.markdown(f"""<div class='metric-box'>
                <div class='metric-val'>{rate:.0%}</div>
                <div class='metric-label'>Success</div>
            </div>""", unsafe_allow_html=True)

        st.markdown(f"""
        <div style='margin-top:10px;font-size:0.78rem;color:#4a6fa5;line-height:2'>
            ⏱ Avg latency: <span style='color:#c8deff'>{metrics.get('avg_latency_s',0):.1f}s</span><br>
            🔤 Total tokens: <span style='color:#c8deff'>{metrics.get('total_tokens_used',0):,}</span><br>
            🔁 Total retries: <span style='color:#c8deff'>{metrics.get('total_retries',0)}</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.caption("No metrics yet")

    st.markdown("---")

    # Task history
    st.markdown("<div style='font-size:0.72rem;color:#4a6fa5;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px'>Recent Tasks</div>", unsafe_allow_html=True)
    tasks_data = api_get("/tasks")
    if tasks_data and tasks_data.get("tasks"):
        for t in tasks_data["tasks"][-5:][::-1]:
            status = t.get("status", "")
            color = {"complete": "#2dbd6e", "failed": "#ff4a4a", "running": "#2a7aff"}.get(status, "#ffb32a")
            short_task = t.get("task", "")[:35] + ("…" if len(t.get("task","")) > 35 else "")
            if st.button(f"{'●'} {short_task}", key=f"hist_{t['task_id']}", use_container_width=True):
                st.session_state.task_id = t["task_id"]
                st.session_state.polling = False
                st.rerun()
    else:
        st.caption("No tasks yet")


# ── Main layout ────────────────────────────────────────────────────────────────
st.markdown("""
<div style='margin-bottom: 28px'>
    <div class='main-title'>Autonomous Agent Workflow</div>
    <div class='main-subtitle'>Powered by Groq LLMs · LangGraph · ChromaDB</div>
</div>
""", unsafe_allow_html=True)

tab_run, tab_monitor, tab_results, tab_tasks = st.tabs([
    "⚡ Run Task", "📡 Monitor", "📋 Results", "🗂 All Tasks"
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — RUN TASK
# ══════════════════════════════════════════════════════════════════════════════
with tab_run:
    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        st.markdown("<div style='font-size:0.72rem;color:#4a6fa5;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px'>Task Description</div>", unsafe_allow_html=True)

        example_choice = st.selectbox(
            "Load example",
            ["— custom —"] + list(EXAMPLE_TASKS.keys()),
            label_visibility="collapsed",
        )

        initial_task = EXAMPLE_TASKS.get(example_choice, "") if example_choice != "— custom —" else ""

        task_text = st.text_area(
            "Task",
            value=initial_task or st.session_state.get("_task_text", ""),
            height=180,
            placeholder="Describe what you want the agent system to research, analyse, and report on…",
            label_visibility="collapsed",
        )
        st.session_state["_task_text"] = task_text

        char_count = len(task_text)
        st.markdown(f"<div style='font-size:0.72rem;color:#4a6fa5;text-align:right'>{char_count} chars</div>", unsafe_allow_html=True)

        col_btn, col_hint = st.columns([1, 2])
        with col_btn:
            submit = st.button("▶ RUN TASK", use_container_width=True, disabled=not healthy)

        if submit and task_text.strip():
            if len(task_text.strip()) < 10:
                st.warning("Task must be at least 10 characters.")
            else:
                with st.spinner("Submitting task…"):
                    resp = api_post("/task", {"task": task_text.strip()})
                if resp:
                    st.session_state.task_id = resp["task_id"]
                    st.session_state.status = None
                    st.session_state.result = None
                    st.session_state.polling = True
                    st.session_state.log = [f"✔ Task submitted — ID: {resp['task_id'][:8]}…"]
                    st.session_state.start_time = time.time()
                    st.success(f"Task accepted! ID: `{resp['task_id'][:8]}…`")
                    time.sleep(0.5)
                    st.rerun()

        if not healthy:
            st.caption("⚠ API offline — start the server first")

    with col_right:
        st.markdown("<div style='font-size:0.72rem;color:#4a6fa5;text-transform:uppercase;letter-spacing:.08em;margin-bottom:12px'>How It Works</div>", unsafe_allow_html=True)

        for name, emoji, desc in AGENT_STEPS:
            st.markdown(f"""
            <div class='agent-card pending'>
                <span style='font-size:1.1rem'>{emoji}</span>
                <div>
                    <div class='agent-name'>{name}</div>
                    <div class='agent-desc'>{desc}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — MONITOR
# ══════════════════════════════════════════════════════════════════════════════
with tab_monitor:
    if not st.session_state.task_id:
        st.markdown("<div style='text-align:center;padding:60px;color:#4a6fa5'>Submit a task to start monitoring.</div>", unsafe_allow_html=True)
    else:
        task_id = st.session_state.task_id
        col_hdr, col_refresh = st.columns([4, 1])
        with col_hdr:
            st.markdown(f"<div style='font-family:Space Mono,monospace;font-size:0.85rem;color:#4a6fa5'>Task ID: <span style='color:#c8deff'>{task_id}</span></div>", unsafe_allow_html=True)
        with col_refresh:
            if st.button("↻ Refresh", use_container_width=True):
                st.rerun()

        status_data = api_get(f"/status/{task_id}")

        if status_data:
            wf_status = status_data.get("workflow_status", "running")
            current_step = status_data.get("current_step", "")
            retry = status_data.get("retry_count", 0)
            elapsed = status_data.get("elapsed_s") or (
                time.time() - st.session_state.start_time
                if st.session_state.start_time else 0
            )

            # Status header
            pill_class = {
                "running": "pill-running", "complete": "pill-complete",
                "failed": "pill-failed", "awaiting_human": "pill-awaiting"
            }.get(wf_status, "pill-running")

            st.markdown(f"""
            <div style='display:flex;align-items:center;gap:16px;margin:16px 0'>
                <span class='pill {pill_class}'>{wf_status.upper()}</span>
                <span style='font-family:Space Mono,monospace;font-size:0.8rem;color:#4a6fa5'>
                    {elapsed:.1f}s elapsed
                    {"  ·  retry #" + str(retry) if retry else ""}
                </span>
            </div>
            """, unsafe_allow_html=True)

            # Progress bar
            step_names = [s[0] for s in AGENT_STEPS]
            curr_idx = step_names.index(current_step) if current_step in step_names else -1
            progress = max(0.0, min(1.0, (curr_idx + 1) / len(AGENT_STEPS))) if wf_status == "running" else (1.0 if wf_status == "complete" else 0.0)
            st.progress(progress)

            # Agent step cards
            col_steps, col_info = st.columns([1, 1], gap="large")

            with col_steps:
                st.markdown("<div style='font-size:0.72rem;color:#4a6fa5;text-transform:uppercase;letter-spacing:.08em;margin:12px 0 8px'>Pipeline Steps</div>", unsafe_allow_html=True)
                for i, (name, emoji, desc) in enumerate(AGENT_STEPS):
                    if wf_status == "complete":
                        card_class, dot_class = "done", "dot-done"
                    elif i < curr_idx:
                        card_class, dot_class = "done", "dot-done"
                    elif i == curr_idx:
                        card_class, dot_class = "active", "dot-active"
                    else:
                        card_class, dot_class = "pending", "dot-pending"

                    st.markdown(f"""
                    <div class='agent-card {card_class}'>
                        <div class='agent-dot {dot_class}'></div>
                        <span style='font-size:1rem'>{emoji}</span>
                        <div>
                            <div class='agent-name'>{name}</div>
                            <div class='agent-desc'>{desc}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            with col_info:
                subtasks = status_data.get("subtasks", [])
                if subtasks:
                    st.markdown("<div style='font-size:0.72rem;color:#4a6fa5;text-transform:uppercase;letter-spacing:.08em;margin:12px 0 8px'>Subtasks</div>", unsafe_allow_html=True)
                    for i, s in enumerate(subtasks):
                        done = wf_status == "complete" or i < curr_idx
                        icon = "✓" if done else ("→" if i == curr_idx else "○")
                        color = "#2dbd6e" if done else ("#2a7aff" if i == curr_idx else "#1e2d42")
                        st.markdown(f"<div style='font-size:0.82rem;color:{color};padding:4px 0;font-family:Space Mono,monospace'>{icon} {s}</div>", unsafe_allow_html=True)

                # Activity log
                if st.session_state.log:
                    st.markdown("<div style='font-size:0.72rem;color:#4a6fa5;text-transform:uppercase;letter-spacing:.08em;margin:16px 0 8px'>Activity Log</div>", unsafe_allow_html=True)
                    for entry in st.session_state.log[-8:]:
                        st.markdown(f"<div style='font-size:0.75rem;color:#4a6fa5;font-family:Space Mono,monospace;padding:2px 0'>{entry}</div>", unsafe_allow_html=True)

            # Human-in-the-loop
            if status_data.get("human_confirmation_needed"):
                st.markdown("---")
                st.warning(f"👤 **Human Review Required**\n\n{status_data.get('human_confirmation_message', '')}")
                hcol1, hcol2, hcol3 = st.columns([1, 1, 3])
                feedback = st.text_input("Optional feedback for the agent:", placeholder="e.g. Simplify the visualisation code")
                with hcol1:
                    if st.button("✅ Proceed", use_container_width=True):
                        api_post(f"/confirm/{task_id}", {"action": "proceed", "feedback": feedback})
                        st.session_state.log.append("👤 Human approved — resuming")
                        st.rerun()
                with hcol2:
                    if st.button("❌ Abort", use_container_width=True):
                        api_post(f"/confirm/{task_id}", {"action": "abort"})
                        st.session_state.log.append("👤 Human aborted task")
                        st.rerun()

            if status_data.get("error"):
                st.error(f"Error: {status_data['error']}")

            # Auto-refresh while running
            if wf_status == "running":
                st.session_state.log.append(f"[{datetime.now().strftime('%H:%M:%S')}] Step: {current_step}")
                time.sleep(3)
                st.rerun()
            elif wf_status == "complete" and not st.session_state.result:
                st.session_state.result = api_get(f"/result/{task_id}")
                st.success("✅ Task complete! View results in the Results tab.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — RESULTS
# ══════════════════════════════════════════════════════════════════════════════
with tab_results:
    task_id = st.session_state.task_id
    if not task_id:
        st.markdown("<div style='text-align:center;padding:60px;color:#4a6fa5'>No task selected.</div>", unsafe_allow_html=True)
    else:
        result = st.session_state.result or api_get(f"/result/{task_id}")
        if result:
            st.session_state.result = result
            wf_status = result.get("status", "")

            if wf_status == "complete":
                # Report
                st.markdown("<div style='font-size:0.72rem;color:#4a6fa5;text-transform:uppercase;letter-spacing:.08em;margin-bottom:12px'>Final Report</div>", unsafe_allow_html=True)
                report = result.get("report", "")
                if report:
                    with st.expander("📄 View Full Report", expanded=True):
                        st.markdown(report)
                    # Download button
                    st.download_button(
                        "⬇ Download Report (.md)",
                        data=report,
                        file_name=f"report_{task_id[:8]}.md",
                        mime="text/markdown",
                    )

                st.markdown("---")
                r1, r2, r3, r4 = st.columns(4)
                token_total = sum(result.get("token_usage", {}).values())
                timing_total = sum(result.get("step_timings", {}).values())
                artifacts_n = len(result.get("artifacts", []))
                sources_n = len(result.get("sources", []))
                for col, val, label in [
                    (r1, f"{token_total:,}", "Tokens Used"),
                    (r2, f"{timing_total:.1f}s", "Total Time"),
                    (r3, str(artifacts_n), "Artifacts"),
                    (r4, str(sources_n), "Sources"),
                ]:
                    col.markdown(f"""<div class='metric-box'>
                        <div class='metric-val' style='font-size:1.4rem'>{val}</div>
                        <div class='metric-label'>{label}</div>
                    </div>""", unsafe_allow_html=True)

                st.markdown("---")
                detail_col1, detail_col2 = st.columns(2)

                with detail_col1:
                    st.markdown("<div style='font-size:0.72rem;color:#4a6fa5;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px'>Token Usage by Agent</div>", unsafe_allow_html=True)
                    token_usage = result.get("token_usage", {})
                    if token_usage:
                        for agent, tokens in sorted(token_usage.items(), key=lambda x: -x[1]):
                            pct = tokens / max(token_total, 1)
                            st.markdown(f"""
                            <div style='margin-bottom:8px'>
                                <div style='display:flex;justify-content:space-between;font-size:0.78rem;margin-bottom:3px'>
                                    <span style='font-family:Space Mono,monospace;color:#c8deff'>{agent}</span>
                                    <span style='color:#4a6fa5'>{tokens:,}</span>
                                </div>
                                <div style='background:#1e2d42;border-radius:4px;height:4px;overflow:hidden'>
                                    <div style='width:{pct*100:.0f}%;height:100%;background:linear-gradient(90deg,#1a4aff,#2dbd6e);border-radius:4px'></div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                with detail_col2:
                    st.markdown("<div style='font-size:0.72rem;color:#4a6fa5;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px'>Step Timings</div>", unsafe_allow_html=True)
                    timings = result.get("step_timings", {})
                    if timings:
                        max_t = max(timings.values()) or 1
                        for agent, secs in sorted(timings.items(), key=lambda x: -x[1]):
                            st.markdown(f"""
                            <div style='margin-bottom:8px'>
                                <div style='display:flex;justify-content:space-between;font-size:0.78rem;margin-bottom:3px'>
                                    <span style='font-family:Space Mono,monospace;color:#c8deff'>{agent}</span>
                                    <span style='color:#4a6fa5'>{secs:.2f}s</span>
                                </div>
                                <div style='background:#1e2d42;border-radius:4px;height:4px;overflow:hidden'>
                                    <div style='width:{secs/max_t*100:.0f}%;height:100%;background:#2a5aff;border-radius:4px'></div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                # Sources
                sources = result.get("sources", [])
                if sources:
                    st.markdown("<div style='font-size:0.72rem;color:#4a6fa5;text-transform:uppercase;letter-spacing:.08em;margin:16px 0 8px'>Research Sources</div>", unsafe_allow_html=True)
                    for s in sources[:8]:
                        st.markdown(f"<div style='font-size:0.78rem;color:#2a7aff;font-family:Space Mono,monospace;padding:3px 0'>🔗 {s}</div>", unsafe_allow_html=True)

                # Artifacts
                artifacts = result.get("artifacts", [])
                if artifacts:
                    st.markdown("<div style='font-size:0.72rem;color:#4a6fa5;text-transform:uppercase;letter-spacing:.08em;margin:16px 0 8px'>Generated Artifacts</div>", unsafe_allow_html=True)
                    for a in artifacts:
                        p = Path(a)
                        if p.exists():
                            if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".svg"):
                                st.image(str(p), caption=p.name, use_container_width=True)
                            else:
                                st.markdown(f"<div style='font-family:Space Mono,monospace;font-size:0.78rem;color:#c8deff;padding:6px 0'>📁 {p.name}</div>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<div style='font-family:Space Mono,monospace;font-size:0.78rem;color:#4a6fa5;padding:6px 0'>📁 {a}</div>", unsafe_allow_html=True)

            elif wf_status == "running":
                st.info("⏳ Task still running… switch to the Monitor tab.")
            else:
                st.error(f"Task ended with status: {wf_status}")
        else:
            st.info("No result available yet.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — ALL TASKS
# ══════════════════════════════════════════════════════════════════════════════
with tab_tasks:
    col_title, col_btn = st.columns([3, 1])
    with col_title:
        st.markdown("<div style='font-size:0.72rem;color:#4a6fa5;text-transform:uppercase;letter-spacing:.08em;margin-bottom:12px'>Task History</div>", unsafe_allow_html=True)
    with col_btn:
        if st.button("↻ Refresh list", use_container_width=True):
            st.rerun()

    tasks_data = api_get("/tasks")
    if tasks_data and tasks_data.get("tasks"):
        tasks = tasks_data["tasks"]
        st.markdown(f"<div style='font-size:0.8rem;color:#4a6fa5;margin-bottom:12px'>{len(tasks)} tasks total</div>", unsafe_allow_html=True)

        for t in reversed(tasks):
            status = t.get("status", "")
            pill_cls = {"complete": "pill-complete", "failed": "pill-failed", "running": "pill-running"}.get(status, "pill-awaiting")
            task_preview = t.get("task", "")[:90] + ("…" if len(t.get("task","")) > 90 else "")
            tid = t.get("task_id", "")

            with st.container():
                row1, row2 = st.columns([5, 1])
                with row1:
                    st.markdown(f"""
                    <div style='background:#0d1520;border:1px solid #1e2d42;border-radius:10px;padding:14px 18px;margin-bottom:8px'>
                        <div style='display:flex;align-items:center;gap:12px;margin-bottom:6px'>
                            <span class='pill {pill_cls}'>{status.upper()}</span>
                            <span style='font-family:Space Mono,monospace;font-size:0.72rem;color:#4a6fa5'>{tid[:8]}…</span>
                            <span style='font-size:0.72rem;color:#1e2d42'>subtasks: {t.get("subtasks",0)} · retries: {t.get("retries",0)}</span>
                        </div>
                        <div style='font-size:0.85rem;color:#c8deff'>{task_preview}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with row2:
                    if st.button("View", key=f"view_{tid}", use_container_width=True):
                        st.session_state.task_id = tid
                        st.session_state.result = None
                        st.rerun()
    else:
        st.markdown("<div style='text-align:center;padding:60px;color:#4a6fa5'>No tasks submitted yet.</div>", unsafe_allow_html=True)

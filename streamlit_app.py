"""
Nexus — Autonomous Multi-Agent AI System
─────────────────────────────────────────
Production frontend. Beautiful, secure, robust.
"""

import time
import uuid
from pathlib import Path

import requests
import streamlit as st

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nexus",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design system ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] { font-family: 'Inter', sans-serif; font-size: 15px; }
.stApp { background: #06090f; }

[data-testid="stSidebar"] {
    background: #09101a !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
}
[data-testid="stSidebar"] * { color: #8a9bbf !important; }
[data-testid="stSidebar"] input {
    background: #0e1826 !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 6px !important;
    color: #c8d8f0 !important;
    font-size: 0.82rem !important;
}

.wordmark {
    font-family: 'Syne', sans-serif;
    font-size: 1.35rem;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.03em;
    line-height: 1;
}
.wordmark span { color: #3d7eff; }

.page-title {
    font-family: 'Syne', sans-serif;
    font-size: 2rem;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.04em;
    line-height: 1.15;
    margin: 0;
}
.page-subtitle {
    font-size: 0.88rem;
    color: #4a6080;
    margin-top: 6px;
}

.section-label {
    font-size: 0.68rem;
    font-weight: 600;
    color: #3a5070;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 10px;
}

.card {
    background: #0c1520;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
    padding: 20px 22px;
}

.badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 11px;
    border-radius: 20px;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
.badge::before {
    content: '';
    width: 6px; height: 6px;
    border-radius: 50%;
    display: block;
}
.badge-running  { background: rgba(61,126,255,0.12); color: #3d7eff; border: 1px solid rgba(61,126,255,0.25); }
.badge-running::before  { background: #3d7eff; animation: blink 1.4s ease-in-out infinite; }
.badge-complete { background: rgba(34,197,100,0.1);  color: #22c564; border: 1px solid rgba(34,197,100,0.2); }
.badge-complete::before { background: #22c564; }
.badge-failed   { background: rgba(255,72,72,0.1);   color: #ff5858; border: 1px solid rgba(255,72,72,0.2); }
.badge-failed::before   { background: #ff5858; }
.badge-awaiting { background: rgba(251,191,36,0.1);  color: #fbbf24; border: 1px solid rgba(251,191,36,0.2); }
.badge-awaiting::before { background: #fbbf24; animation: blink 1.4s ease-in-out infinite; }
.badge-online   { background: rgba(34,197,100,0.08); color: #22c564; border: 1px solid rgba(34,197,100,0.15); }
.badge-online::before   { background: #22c564; }
.badge-offline  { background: rgba(255,255,255,0.05); color: #4a6080; border: 1px solid rgba(255,255,255,0.08); }
.badge-offline::before  { background: #4a6080; }

@keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.25; }
}

.step-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 14px;
    border-radius: 8px;
    margin-bottom: 4px;
}
.step-row.done    { background: rgba(34,197,100,0.05); }
.step-row.active  { background: rgba(61,126,255,0.08); border: 1px solid rgba(61,126,255,0.18); }
.step-row.pending { opacity: 0.3; }

.step-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.step-dot.done    { background: #22c564; }
.step-dot.active  { background: #3d7eff; box-shadow: 0 0 8px rgba(61,126,255,0.7); animation: blink 1.4s ease-in-out infinite; }
.step-dot.pending { background: #1e2d42; }

.step-name { font-size: 0.82rem; font-weight: 500; color: #c0d0e8; }
.step-desc { font-size: 0.71rem; color: #3a5070; margin-top: 1px; }

.stat-block {
    background: #0c1520;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    padding: 16px 18px;
    text-align: center;
}
.stat-val {
    font-family: 'Syne', sans-serif;
    font-size: 1.6rem;
    font-weight: 700;
    color: #3d7eff;
    line-height: 1;
}
.stat-label {
    font-size: 0.67rem;
    font-weight: 600;
    color: #3a5070;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-top: 5px;
}

.bar-track { background: rgba(255,255,255,0.05); border-radius: 3px; height: 3px; overflow: hidden; margin-top: 5px; }
.bar-blue  { height: 100%; border-radius: 3px; background: #3d7eff; }
.bar-green { height: 100%; border-radius: 3px; background: #22c564; }

.notice {
    padding: 14px 18px;
    border-radius: 8px;
    font-size: 0.84rem;
    line-height: 1.55;
    margin-bottom: 14px;
}
.notice-warn    { background: rgba(251,191,36,0.07);  border: 1px solid rgba(251,191,36,0.18);  color: #d4a020; }
.notice-success { background: rgba(34,197,100,0.07);  border: 1px solid rgba(34,197,100,0.18);  color: #1aaa54; }
.notice-error   { background: rgba(255,72,72,0.07);   border: 1px solid rgba(255,72,72,0.18);   color: #c04040; }
.notice-info    { background: rgba(61,126,255,0.07);  border: 1px solid rgba(61,126,255,0.18);  color: #5080c0; }
.notice-title   { font-weight: 600; margin-bottom: 3px; }

div[data-testid="stButton"] > button {
    background: #3d7eff !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.84rem !important;
    padding: 0.55rem 1.5rem !important;
    transition: all 0.15s ease !important;
    letter-spacing: 0.01em !important;
}
div[data-testid="stButton"] > button:hover {
    background: #2d6aef !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 24px rgba(61,126,255,0.28) !important;
}

textarea, .stTextInput input {
    background: #0c1520 !important;
    color: #c0d0e8 !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.9rem !important;
}
textarea:focus, .stTextInput input:focus {
    border-color: rgba(61,126,255,0.35) !important;
    box-shadow: 0 0 0 3px rgba(61,126,255,0.07) !important;
}

[data-testid="stSelectbox"] > div > div {
    background: #0c1520 !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 8px !important;
    color: #c0d0e8 !important;
}

button[data-baseweb="tab"] {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    color: #3a5070 !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #c0d0e8 !important;
    font-weight: 600 !important;
}
[data-testid="stTabContent"] { padding-top: 20px !important; }

[data-testid="stProgress"] > div > div { background: #3d7eff !important; border-radius: 4px !important; }
[data-testid="stProgress"] > div { background: rgba(255,255,255,0.05) !important; border-radius: 4px !important; }

[data-testid="stDownloadButton"] > button {
    background: transparent !important;
    color: #3d7eff !important;
    border: 1px solid rgba(61,126,255,0.3) !important;
    border-radius: 6px !important;
    font-size: 0.8rem !important;
    padding: 0.4rem 1.2rem !important;
    box-shadow: none !important;
}
[data-testid="stDownloadButton"] > button:hover {
    background: rgba(61,126,255,0.07) !important;
    transform: none !important;
    box-shadow: none !important;
}

.stExpander {
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 8px !important;
    background: #0c1520 !important;
}

hr { border-color: rgba(255,255,255,0.05) !important; margin: 22px 0 !important; }
.block-container { padding-top: 2.5rem !important; max-width: 1280px !important; }
#MainMenu, footer, header { visibility: hidden; }
label {
    color: #3a5070 !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
}

[data-testid="stSidebar"] div[data-testid="stButton"] > button {
    background: transparent !important;
    color: #4a6080 !important;
    border: 1px solid rgba(255,255,255,0.05) !important;
    font-size: 0.77rem !important;
    padding: 0.38rem 0.8rem !important;
    font-weight: 400 !important;
    box-shadow: none !important;
    text-align: left !important;
}
[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {
    background: rgba(61,126,255,0.07) !important;
    color: #8aacce !important;
    transform: none !important;
    box-shadow: none !important;
    border-color: rgba(61,126,255,0.18) !important;
}
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
AGENT_STEPS = [
    ("Planner",    "Breaks the task into ordered subtasks"),
    ("Researcher", "Web search and knowledge retrieval"),
    ("Coder",      "Generates Python analysis code"),
    ("Executor",   "Runs code in a secure sandbox"),
    ("Critic",     "Evaluates and validates the output"),
    ("Reporter",   "Compiles the final report"),
]

STEP_KEY_MAP = {
    "PlannerAgent":   0,
    "ResearchAgent":  1,
    "CoderAgent":     2,
    "ExecutorAgent":  3,
    "CriticAgent":    4,
    "ReporterAgent":  5,
}

EXAMPLE_TASKS = {
    "Solar energy trends": (
        "Analyse global solar energy capacity growth from 2010 to 2023. "
        "Generate synthetic data by region (China, USA, Europe, Rest of World). "
        "Create a line chart of total capacity over time and a bar chart of regional breakdown. "
        "Identify the top growth markets and write a structured report with key insights."
    ),
    "EV adoption analysis": (
        "Research electric vehicle adoption trends from 2018 to 2024. "
        "Generate a synthetic dataset with regional EV sales and market share. "
        "Perform statistical analysis, create visualisations, and produce a report "
        "with the top three growth markets and key adoption drivers."
    ),
    "E-commerce performance": (
        "Analyse e-commerce sales performance across product categories. "
        "Generate synthetic monthly sales data for 5 categories over 3 years. "
        "Compute growth rates, seasonal patterns, and top performers. "
        "Create charts and write an executive summary with recommendations."
    ),
    "Stock volatility study": (
        "Analyse stock market volatility patterns in the tech sector 2020–2024. "
        "Generate synthetic OHLCV data for 5 companies. Calculate rolling volatility, "
        "Sharpe ratios and drawdowns. Create charts and write a risk analysis report."
    ),
}

# ── Error messages — never expose raw server errors to users ───────────────────
def _friendly_error(exc=None, status_code=None) -> str:
    if status_code == 404:
        return "The requested resource could not be found."
    if status_code == 422:
        return "The request was invalid. Please check your input."
    if status_code in (500, 502, 503, 504):
        return "The server is temporarily unavailable. It may be starting up — please try again in 30 seconds."
    if exc is not None:
        msg = str(exc).lower()
        if any(w in msg for w in ("connection", "refused", "unreachable", "network")):
            return "Unable to reach the server. Please verify the API host in the sidebar."
        if "timeout" in msg:
            return "The request timed out. The server may be under load — please try again."
    return "Something went wrong. Please try again in a moment."


# ── Session state ──────────────────────────────────────────────────────────────
DEFAULTS = {
    "task_id": None,
    "result": None,
    "log": [],
    "api_host": "https://nexus-production-ebd3.up.railway.app",
    "start_time": None,
    "submit_error": None,
    "api_online": None,
    "session_token": None,
    "owned_task_ids": [],   # task IDs submitted by this browser session only
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Assign a unique token to this browser session (persists across reruns)
if not st.session_state.session_token:
    st.session_state.session_token = str(uuid.uuid4())


# ── API layer ──────────────────────────────────────────────────────────────────
def api_get(path: str, timeout: int = 8):
    try:
        r = requests.get(f"{st.session_state.api_host}{path}", timeout=timeout)
        return (r.json(), None) if r.ok else (None, _friendly_error(status_code=r.status_code))
    except Exception as e:
        return None, _friendly_error(exc=e)


def api_post(path: str, data: dict, timeout: int = 12):
    try:
        r = requests.post(f"{st.session_state.api_host}{path}", json=data, timeout=timeout)
        return (r.json(), None) if r.ok else (None, _friendly_error(status_code=r.status_code))
    except Exception as e:
        return None, _friendly_error(exc=e)


def fetch_image(url: str):
    try:
        r = requests.get(url, timeout=12)
        return r.content if r.ok else None
    except Exception:
        return None


def check_health() -> bool:
    data, _ = api_get("/health", timeout=5)
    online = data is not None and data.get("status") == "healthy"
    st.session_state.api_online = online
    return online


# ── UI helpers ─────────────────────────────────────────────────────────────────
def notice(kind: str, title: str, body: str = "") -> None:
    st.markdown(
        f"<div class='notice notice-{kind}'>"
        f"<div class='notice-title'>{title}</div>"
        + (f"<div style='margin-top:2px'>{body}</div>" if body else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def badge_html(status: str) -> str:
    labels = {"running": "Running", "complete": "Complete", "failed": "Failed", "awaiting_human": "Needs review"}
    classes = {"running": "badge-running", "complete": "badge-complete", "failed": "badge-failed", "awaiting_human": "badge-awaiting"}
    return f"<span class='badge {classes.get(status, 'badge-offline')}'>{labels.get(status, status.title())}</span>"


def stat_block_html(value: str, label: str) -> str:
    return f"<div class='stat-block'><div class='stat-val'>{value}</div><div class='stat-label'>{label}</div></div>"


def bar_row_html(label: str, value: str, pct: float, color: str = "blue") -> str:
    return (
        f"<div style='margin-bottom:11px'>"
        f"<div style='display:flex;justify-content:space-between;font-size:0.78rem'>"
        f"<span style='color:#8a9bbf'>{label}</span>"
        f"<span style='color:#3a5070;font-variant-numeric:tabular-nums'>{value}</span></div>"
        f"<div class='bar-track'><div class='bar-{color}' style='width:{min(pct*100,100):.0f}%'></div></div>"
        f"</div>"
    )


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<div style='padding:4px 0 24px'>"
        "<div class='wordmark'>Nexus<span>.</span></div>"
        "<div style='font-size:0.68rem;color:#2a3a50;margin-top:4px;letter-spacing:0.08em;text-transform:uppercase'>Multi-Agent AI</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='section-label'>API Host</div>", unsafe_allow_html=True)
    host_input = st.text_input("host", value=st.session_state.api_host, label_visibility="collapsed")
    st.session_state.api_host = host_input.rstrip("/")

    healthy = check_health()
    status_badge = "<span class='badge badge-online'>Connected</span>" if healthy else "<span class='badge badge-offline'>Offline</span>"
    st.markdown(f"<div style='margin:6px 0 20px'>{status_badge}</div>", unsafe_allow_html=True)
    if not healthy:
        st.markdown(
            "<div style='font-size:0.75rem;color:#2a3a50;line-height:1.55;margin-bottom:16px'>"
            "Cannot reach the server. Check the host above or ensure the API is running."
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<div class='section-label'>System</div>", unsafe_allow_html=True)

    metrics, _ = api_get("/metrics")
    if metrics:
        c1, c2 = st.columns(2)
        c1.markdown(stat_block_html(str(metrics.get("total_tasks", 0)), "Tasks"), unsafe_allow_html=True)
        c2.markdown(stat_block_html(f"{metrics.get('task_success_rate', 0):.0%}", "Success"), unsafe_allow_html=True)
        st.markdown(
            f"<div style='font-size:0.76rem;line-height:2.1;color:#3a5070;margin-top:10px'>"
            f"Avg time &nbsp;<span style='color:#5a7a9a'>{metrics.get('avg_latency_s',0):.1f}s</span><br>"
            f"Tokens &nbsp;&nbsp;&nbsp;<span style='color:#5a7a9a'>{metrics.get('total_tokens_used',0):,}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown("<div style='font-size:0.76rem;color:#2a3a50'>No data yet.</div>", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<div class='section-label'>Recent</div>", unsafe_allow_html=True)

    tasks_data, _ = api_get("/tasks")
    owned = set(st.session_state.owned_task_ids)
    my_tasks = [t for t in (tasks_data or {}).get("tasks", []) if t.get("task_id") in owned]
    if my_tasks:
        for t in list(reversed(my_tasks))[:6]:
            preview = t.get("task", "")[:36] + ("…" if len(t.get("task", "")) > 36 else "")
            if st.button(preview, key=f"side_{t['task_id']}", use_container_width=True):
                st.session_state.task_id = t["task_id"]
                st.session_state.result = None
                st.rerun()
    else:
        st.markdown("<div style='font-size:0.76rem;color:#2a3a50'>No history yet.</div>", unsafe_allow_html=True)


# ── Main layout ────────────────────────────────────────────────────────────────
st.markdown(
    "<div style='margin-bottom:30px'>"
    "<div class='page-title'>Agent Workspace</div>"
    "<div class='page-subtitle'>Submit a task and let the pipeline research, code, execute, and report.</div>"
    "</div>",
    unsafe_allow_html=True,
)

tab_run, tab_monitor, tab_results, tab_history = st.tabs(
    ["New Task", "Monitor", "Results", "History"]
)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — NEW TASK
# ══════════════════════════════════════════════════════════════════════════════
with tab_run:
    col_form, col_steps = st.columns([3, 2], gap="large")

    with col_form:
        st.markdown("<div class='section-label'>Task</div>", unsafe_allow_html=True)

        example = st.selectbox("examples", ["Write your own…"] + list(EXAMPLE_TASKS.keys()), label_visibility="collapsed")
        prefill = EXAMPLE_TASKS.get(example, "")

        task_text = st.text_area(
            "task",
            value=prefill or st.session_state.get("_task_draft", ""),
            height=160,
            placeholder="Describe what you want the system to research, analyse, and report on…",
            label_visibility="collapsed",
        )
        if not prefill:
            st.session_state["_task_draft"] = task_text

        btn_col, char_col = st.columns([1, 1])
        with btn_col:
            run_clicked = st.button("Run task", use_container_width=True, disabled=not healthy)
        with char_col:
            st.markdown(
                f"<div style='font-size:0.71rem;color:#2a3a50;padding-top:10px;text-align:right'>{len(task_text)} chars</div>",
                unsafe_allow_html=True,
            )

        if st.session_state.submit_error:
            notice("error", st.session_state.submit_error)

        if not healthy:
            notice("warn", "Server unreachable", "Verify the API host in the sidebar before submitting.")

        if run_clicked:
            st.session_state.submit_error = None
            if len(task_text.strip()) < 10:
                st.session_state.submit_error = "Please write a more detailed task description."
                st.rerun()
            else:
                with st.spinner("Submitting…"):
                    resp, err = api_post("/task", {"task": task_text.strip()})
                if err:
                    st.session_state.submit_error = err
                    st.rerun()
                else:
                    st.session_state.task_id = resp["task_id"]
                    st.session_state.result = None
                    st.session_state.log = []
                    st.session_state.start_time = time.time()
                    st.session_state.submit_error = None
                    st.session_state.owned_task_ids.append(resp["task_id"])
                    notice("success", "Task submitted", "Switch to the Monitor tab to follow progress.")
                    time.sleep(0.7)
                    st.rerun()

    with col_steps:
        st.markdown("<div class='section-label'>Pipeline overview</div>", unsafe_allow_html=True)
        for name, desc in AGENT_STEPS:
            st.markdown(
                f"<div class='step-row pending'>"
                f"<div class='step-dot pending'></div>"
                f"<div><div class='step-name'>{name}</div><div class='step-desc'>{desc}</div></div>"
                f"</div>",
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — MONITOR
# ══════════════════════════════════════════════════════════════════════════════
with tab_monitor:
    if not st.session_state.task_id:
        st.markdown("<div style='padding:48px 0;text-align:center;color:#2a3a50;font-size:0.88rem'>Submit a task first.</div>", unsafe_allow_html=True)
    else:
        task_id = st.session_state.task_id
        h1, h2 = st.columns([5, 1])
        with h1:
            st.markdown(f"<div style='font-size:0.72rem;color:#2a3a50;font-family:monospace'>ID: {task_id}</div>", unsafe_allow_html=True)
        with h2:
            if st.button("Refresh", use_container_width=True):
                st.rerun()

        status_data, status_err = api_get(f"/status/{task_id}")

        if status_err:
            notice("warn", "Status unavailable", status_err)
        elif status_data:
            wf_status = status_data.get("workflow_status", "running")
            current_step = status_data.get("current_step", "")
            retry = status_data.get("retry_count", 0)
            elapsed = status_data.get("elapsed_s") or (
                time.time() - st.session_state.start_time if st.session_state.start_time else 0
            )
            curr_idx = STEP_KEY_MAP.get(current_step, -1)

            st.markdown(
                f"<div style='display:flex;align-items:center;gap:14px;margin:10px 0 18px'>"
                f"{badge_html(wf_status)}"
                f"<span style='font-size:0.76rem;color:#3a5070'>{elapsed:.0f}s</span>"
                + (f"<span style='font-size:0.76rem;color:#c09020'>Retry {retry} of 3</span>" if retry else "")
                + "</div>",
                unsafe_allow_html=True,
            )

            pct = (curr_idx + 1) / len(AGENT_STEPS) if wf_status == "running" and curr_idx >= 0 else (1.0 if wf_status == "complete" else 0.0)
            st.progress(min(pct, 1.0))
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

            pipe_col, info_col = st.columns([1, 1], gap="large")

            with pipe_col:
                st.markdown("<div class='section-label'>Steps</div>", unsafe_allow_html=True)
                for i, (name, desc) in enumerate(AGENT_STEPS):
                    if wf_status == "complete" or i < curr_idx:
                        rc, dc = "done", "done"
                    elif i == curr_idx:
                        rc, dc = "active", "active"
                    else:
                        rc, dc = "pending", "pending"
                    st.markdown(
                        f"<div class='step-row {rc}'>"
                        f"<div class='step-dot {dc}'></div>"
                        f"<div><div class='step-name'>{name}</div><div class='step-desc'>{desc}</div></div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

            with info_col:
                subtasks = status_data.get("subtasks", [])
                if subtasks:
                    st.markdown("<div class='section-label'>Subtasks</div>", unsafe_allow_html=True)
                    for i, s in enumerate(subtasks):
                        done_s = wf_status == "complete" or i < curr_idx
                        active_s = i == curr_idx and wf_status == "running"
                        color = "#22c564" if done_s else ("#3d7eff" if active_s else "#1e2d42")
                        marker = "·" if done_s else ("›" if active_s else "·")
                        st.markdown(
                            f"<div style='font-size:0.79rem;color:{color};padding:4px 0;display:flex;gap:8px'>"
                            f"<span style='flex-shrink:0;color:{color}'>{marker}</span><span>{s}</span></div>",
                            unsafe_allow_html=True,
                        )

            # Human review panel
            if status_data.get("human_confirmation_needed"):
                st.markdown("<hr>", unsafe_allow_html=True)
                notice("warn", "Review required",
                    "The system flagged this output before continuing. "
                    "You can provide guidance below or proceed as-is.")
                feedback = st.text_input(
                    "Guidance for the agent (optional)",
                    placeholder="e.g. Use more realistic data ranges",
                )
                b1, b2, _ = st.columns([1, 1, 3])
                with b1:
                    if st.button("Continue", use_container_width=True):
                        _, err = api_post(f"/confirm/{task_id}", {"action": "proceed", "feedback": feedback or ""})
                        if err:
                            notice("error", "Could not resume", err)
                        else:
                            st.rerun()
                with b2:
                    if st.button("Stop task", use_container_width=True):
                        _, err = api_post(f"/confirm/{task_id}", {"action": "abort"})
                        if err:
                            notice("error", "Could not stop task", err)
                        else:
                            st.rerun()

            # Terminal states
            if wf_status == "failed":
                notice("error", "Task did not complete",
                    "The pipeline encountered an issue it could not recover from. "
                    "Try again with a more specific task description.")
            elif wf_status == "complete":
                notice("success", "Complete", "View the report in the Results tab.")

            # Auto-refresh
            if wf_status == "running":
                time.sleep(3)
                st.rerun()
            elif wf_status == "complete" and not st.session_state.result:
                st.session_state.result, _ = api_get(f"/result/{task_id}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — RESULTS
# ══════════════════════════════════════════════════════════════════════════════
with tab_results:
    task_id = st.session_state.task_id
    if not task_id:
        st.markdown("<div style='padding:48px 0;text-align:center;color:#2a3a50;font-size:0.88rem'>No task selected.</div>", unsafe_allow_html=True)
    else:
        result = st.session_state.result
        if not result:
            result, err = api_get(f"/result/{task_id}")
            if result:
                st.session_state.result = result
            elif err:
                notice("info", "Result not available yet", "The task may still be running. Check the Monitor tab.")
                result = None

        if result:
            wf_status = result.get("status", "")

            if wf_status == "running":
                notice("info", "Still running", "Check the Monitor tab for live progress.")

            elif wf_status == "complete":
                report = result.get("report", "")
                if report:
                    st.markdown("<div class='section-label'>Report</div>", unsafe_allow_html=True)
                    with st.expander("Read full report", expanded=True):
                        st.markdown(report)
                    st.download_button(
                        "Download report",
                        data=report,
                        file_name=f"report_{task_id[:8]}.md",
                        mime="text/markdown",
                    )
                    st.markdown("<hr>", unsafe_allow_html=True)

                token_total  = sum(result.get("token_usage", {}).values())
                timing_total = sum(result.get("step_timings", {}).values())
                artifacts_n  = len(result.get("artifacts", []))
                sources_n    = len(result.get("sources", []))

                c1, c2, c3, c4 = st.columns(4)
                for col, val, lbl in [
                    (c1, f"{token_total:,}", "Tokens"),
                    (c2, f"{timing_total:.1f}s", "Total time"),
                    (c3, str(artifacts_n), "Files"),
                    (c4, str(sources_n), "Sources"),
                ]:
                    col.markdown(stat_block_html(val, lbl), unsafe_allow_html=True)

                st.markdown("<hr>", unsafe_allow_html=True)
                bc1, bc2 = st.columns(2, gap="large")

                with bc1:
                    st.markdown("<div class='section-label'>Token usage</div>", unsafe_allow_html=True)
                    for agent, tokens in sorted(result.get("token_usage", {}).items(), key=lambda x: -x[1]):
                        st.markdown(bar_row_html(agent, f"{tokens:,}", tokens / max(token_total, 1), "blue"), unsafe_allow_html=True)

                with bc2:
                    st.markdown("<div class='section-label'>Time per step</div>", unsafe_allow_html=True)
                    timings = result.get("step_timings", {})
                    max_t = max(timings.values(), default=1)
                    for agent, secs in sorted(timings.items(), key=lambda x: -x[1]):
                        st.markdown(bar_row_html(agent, f"{secs:.2f}s", secs / max_t, "green"), unsafe_allow_html=True)

                sources = result.get("sources", [])
                if sources:
                    st.markdown("<hr>", unsafe_allow_html=True)
                    st.markdown("<div class='section-label'>Sources</div>", unsafe_allow_html=True)
                    for s in sources[:8]:
                        st.markdown(
                            f"<div style='font-size:0.78rem;padding:4px 0;word-break:break-all'>"
                            f"<a href='{s}' target='_blank' style='color:#3d7eff;text-decoration:none'>{s}</a></div>",
                            unsafe_allow_html=True,
                        )

                artifacts = result.get("artifacts", [])
                images = [a for a in artifacts if Path(a).suffix.lower() in (".png", ".jpg", ".jpeg")]
                if images:
                    st.markdown("<hr>", unsafe_allow_html=True)
                    st.markdown("<div class='section-label'>Charts</div>", unsafe_allow_html=True)
                    for a in images:
                        filename = Path(a).name
                        url = f"{st.session_state.api_host}/artifacts/{task_id}/{filename}"
                        img_bytes = fetch_image(url)
                        if img_bytes:
                            st.image(img_bytes, use_container_width=True)
                            st.download_button(
                                f"Download {filename}",
                                data=img_bytes,
                                file_name=filename,
                                mime="image/png",
                                key=f"dl_{filename}",
                            )
                        else:
                            st.markdown(
                                f"<div style='font-size:0.78rem;color:#2a3a50;padding:6px 0'>{filename} — not available</div>",
                                unsafe_allow_html=True,
                            )

            elif wf_status == "failed":
                notice("error", "Task did not complete",
                    "The pipeline could not recover. Try again with a more specific description.")

            elif wf_status == "awaiting_human":
                notice("warn", "Waiting for review", "Go to the Monitor tab to continue or stop the task.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — HISTORY
# ══════════════════════════════════════════════════════════════════════════════
with tab_history:
    hc, rc = st.columns([5, 1])
    with rc:
        if st.button("Refresh", use_container_width=True, key="hist_ref"):
            st.rerun()

    tasks_data, tasks_err = api_get("/tasks")
    owned = set(st.session_state.owned_task_ids)

    if tasks_err:
        notice("warn", "Could not load history", tasks_err)
    elif tasks_data and tasks_data.get("tasks"):
        tasks = list(reversed([t for t in tasks_data["tasks"] if t.get("task_id") in owned]))
        st.markdown(
            f"<div style='font-size:0.76rem;color:#3a5070;margin-bottom:16px'>{len(tasks)} task{'s' if len(tasks)!=1 else ''}</div>",
            unsafe_allow_html=True,
        )
        for t in tasks:
            status = t.get("status", "unknown")
            preview = t.get("task", "")[:110] + ("…" if len(t.get("task","")) > 110 else "")
            tid = t.get("task_id", "")
            sub = t.get("subtasks", 0)
            ret = t.get("retries", 0)

            rl, rr = st.columns([6, 1])
            with rl:
                retry_str = f" · {ret} retr{'ies' if ret!=1 else 'y'}" if ret else ""
                st.markdown(
                    f"<div class='card' style='margin-bottom:8px'>"
                    f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:8px'>"
                    f"{badge_html(status)}"
                    f"<span style='font-size:0.68rem;font-family:monospace;color:#2a3a50'>{tid[:8]}</span>"
                    f"<span style='font-size:0.68rem;color:#2a3a50;margin-left:auto'>{sub} subtask{'s' if sub!=1 else ''}{retry_str}</span>"
                    f"</div>"
                    f"<div style='font-size:0.83rem;color:#8a9bbf;line-height:1.5'>{preview}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with rr:
                if st.button("Open", key=f"open_{tid}", use_container_width=True):
                    if tid in owned:
                        st.session_state.task_id = tid
                        st.session_state.result = None
                        st.rerun()
    else:
        st.markdown(
            "<div style='padding:48px 0;text-align:center;color:#2a3a50;font-size:0.88rem'>No tasks yet.</div>",
            unsafe_allow_html=True,
        )
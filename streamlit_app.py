import time
import uuid
from pathlib import Path

import requests
import streamlit as st

st.set_page_config(page_title="Nexus", layout="wide", initial_sidebar_state="expanded")

# ── Styles ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Inter:wght@300;400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #06090f; }

[data-testid="stSidebar"] { background: #09101a !important; border-right: 1px solid rgba(255,255,255,0.06) !important; }
[data-testid="stSidebar"] * { color: #8a9bbf !important; }
[data-testid="stSidebar"] input { background: #0e1826 !important; border: 1px solid rgba(255,255,255,0.08) !important; border-radius: 6px !important; color: #c8d8f0 !important; font-size: 0.82rem !important; }

.wordmark { font-family: 'Syne', sans-serif; font-size: 1.35rem; font-weight: 800; color: #ffffff; letter-spacing: -0.03em; }
.wordmark span { color: #3d7eff; }
.page-title { font-family: 'Syne', sans-serif; font-size: 1.9rem; font-weight: 700; color: #ffffff; letter-spacing: -0.04em; margin: 0; }
.page-subtitle { font-size: 0.87rem; color: #4a6080; margin-top: 5px; }
.section-label { font-size: 0.68rem; font-weight: 600; color: #3a5070; text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 10px; }

.card { background: #0c1520; border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 20px 22px; }

.badge { display: inline-flex; align-items: center; gap: 6px; padding: 4px 11px; border-radius: 20px; font-size: 0.68rem; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; }
.badge::before { content: ''; width: 6px; height: 6px; border-radius: 50%; display: block; }
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
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.25; } }

.step-row { display: flex; align-items: center; gap: 12px; padding: 10px 14px; border-radius: 8px; margin-bottom: 4px; }
.step-row.done   { background: rgba(34,197,100,0.05); }
.step-row.active { background: rgba(61,126,255,0.08); border: 1px solid rgba(61,126,255,0.18); }
.step-row.pending { opacity: 0.3; }
.step-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.step-dot.done   { background: #22c564; }
.step-dot.active { background: #3d7eff; box-shadow: 0 0 8px rgba(61,126,255,0.7); animation: blink 1.4s infinite; }
.step-dot.pending { background: #1e2d42; }
.step-name { font-size: 0.82rem; font-weight: 500; color: #c0d0e8; }
.step-desc { font-size: 0.71rem; color: #3a5070; margin-top: 1px; }

.stat-block { background: #0c1520; border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 16px 18px; text-align: center; }
.stat-val { font-family: 'Syne', sans-serif; font-size: 1.6rem; font-weight: 700; color: #3d7eff; line-height: 1; }
.stat-label { font-size: 0.67rem; font-weight: 600; color: #3a5070; text-transform: uppercase; letter-spacing: 0.1em; margin-top: 5px; }

.bar-track { background: rgba(255,255,255,0.05); border-radius: 3px; height: 3px; overflow: hidden; margin-top: 5px; }
.bar-blue  { height: 100%; border-radius: 3px; background: #3d7eff; }
.bar-green { height: 100%; border-radius: 3px; background: #22c564; }

.notice { padding: 14px 18px; border-radius: 8px; font-size: 0.84rem; line-height: 1.55; margin-bottom: 14px; }
.notice-warn    { background: rgba(251,191,36,0.07);  border: 1px solid rgba(251,191,36,0.18);  color: #d4a020; }
.notice-success { background: rgba(34,197,100,0.07);  border: 1px solid rgba(34,197,100,0.18);  color: #1aaa54; }
.notice-error   { background: rgba(255,72,72,0.07);   border: 1px solid rgba(255,72,72,0.18);   color: #c04040; }
.notice-info    { background: rgba(61,126,255,0.07);  border: 1px solid rgba(61,126,255,0.18);  color: #5080c0; }
.notice-title   { font-weight: 600; margin-bottom: 3px; }

/* Chat bubbles */
.chat-user { background: rgba(61,126,255,0.12); border: 1px solid rgba(61,126,255,0.2); border-radius: 12px 12px 4px 12px; padding: 12px 16px; margin: 8px 0; font-size: 0.88rem; color: #c8d8f0; max-width: 85%; margin-left: auto; }
.chat-assistant { background: #0c1520; border: 1px solid rgba(255,255,255,0.07); border-radius: 12px 12px 12px 4px; padding: 12px 16px; margin: 8px 0; font-size: 0.88rem; color: #8aacce; max-width: 85%; }
.chat-intent { font-size: 0.68rem; color: #3a5070; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 6px; }
.chat-wrap { max-height: 420px; overflow-y: auto; padding: 4px 0; }

div[data-testid="stButton"] > button { background: #3d7eff !important; color: #fff !important; border: none !important; border-radius: 8px !important; font-family: 'Inter', sans-serif !important; font-weight: 600 !important; font-size: 0.84rem !important; padding: 0.55rem 1.5rem !important; transition: all 0.15s ease !important; }
div[data-testid="stButton"] > button:hover { background: #2d6aef !important; transform: translateY(-1px) !important; box-shadow: 0 6px 24px rgba(61,126,255,0.28) !important; }

textarea, .stTextInput input { background: #0c1520 !important; color: #c0d0e8 !important; border: 1px solid rgba(255,255,255,0.08) !important; border-radius: 8px !important; font-family: 'Inter', sans-serif !important; font-size: 0.9rem !important; }
[data-testid="stSelectbox"] > div > div { background: #0c1520 !important; border: 1px solid rgba(255,255,255,0.08) !important; border-radius: 8px !important; color: #c0d0e8 !important; }

button[data-baseweb="tab"] { font-family: 'Inter', sans-serif !important; font-size: 0.82rem !important; font-weight: 500 !important; color: #3a5070 !important; }
button[data-baseweb="tab"][aria-selected="true"] { color: #c0d0e8 !important; font-weight: 600 !important; }

[data-testid="stProgress"] > div > div { background: #3d7eff !important; border-radius: 4px !important; }
[data-testid="stProgress"] > div { background: rgba(255,255,255,0.05) !important; border-radius: 4px !important; }

[data-testid="stDownloadButton"] > button { background: transparent !important; color: #3d7eff !important; border: 1px solid rgba(61,126,255,0.3) !important; border-radius: 6px !important; font-size: 0.8rem !important; padding: 0.4rem 1.2rem !important; box-shadow: none !important; }
[data-testid="stDownloadButton"] > button:hover { background: rgba(61,126,255,0.07) !important; transform: none !important; box-shadow: none !important; }

.stExpander { border: 1px solid rgba(255,255,255,0.06) !important; border-radius: 8px !important; background: #0c1520 !important; }
hr { border-color: rgba(255,255,255,0.05) !important; margin: 22px 0 !important; }
.block-container { padding-top: 2.5rem !important; max-width: 1280px !important; }
#MainMenu, footer, header { visibility: hidden; }
label { color: #3a5070 !important; font-size: 0.7rem !important; font-weight: 600 !important; text-transform: uppercase !important; letter-spacing: 0.1em !important; }

[data-testid="stSidebar"] div[data-testid="stButton"] > button { background: transparent !important; color: #4a6080 !important; border: 1px solid rgba(255,255,255,0.05) !important; font-size: 0.77rem !important; padding: 0.38rem 0.8rem !important; font-weight: 400 !important; box-shadow: none !important; }
[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover { background: rgba(61,126,255,0.07) !important; color: #8aacce !important; transform: none !important; box-shadow: none !important; }
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
STEP_KEY_MAP = {"PlannerAgent": 0, "ResearchAgent": 1, "CoderAgent": 2, "ExecutorAgent": 3, "CriticAgent": 4, "ReporterAgent": 5}

EXAMPLE_TASKS = {
    "Solar energy trends": "Analyse global solar energy capacity growth from 2010 to 2023. Generate synthetic data by region (China, USA, Europe, Rest of World). Create a line chart of total capacity over time and a bar chart of regional breakdown. Identify the top growth markets and write a structured report with key insights.",
    "EV adoption analysis": "Research electric vehicle adoption trends from 2018 to 2024. Generate a synthetic dataset with regional EV sales and market share. Perform statistical analysis, create visualisations, and produce a report with the top three growth markets and key adoption drivers.",
    "E-commerce performance": "Analyse e-commerce sales performance across product categories. Generate synthetic monthly sales data for 5 categories over 3 years. Compute growth rates, seasonal patterns, and top performers. Create charts and write an executive summary with recommendations.",
}

# ── Error messages ─────────────────────────────────────────────────────────────
def _friendly_error(exc=None, status_code=None) -> str:
    if status_code == 403: return "You don't have access to this resource."
    if status_code == 404: return "The requested resource could not be found."
    if status_code == 422: return "The request was invalid. Please check your input."
    if status_code in (500, 502, 503, 504): return "The server is temporarily unavailable. Please try again in 30 seconds."
    if exc is not None:
        msg = str(exc).lower()
        if any(w in msg for w in ("connection", "refused", "unreachable", "network")): return "Unable to reach the server. Verify the API host in the sidebar."
        if "timeout" in msg: return "The request timed out. Please try again."
    return "Something went wrong. Please try again."

# ── Session state ──────────────────────────────────────────────────────────────
DEFAULTS = {
    "session_id": None,
    "task_id": None,
    "result": None,
    "log": [],
    "api_host": "https://nexus-production-ebd3.up.railway.app",
    "start_time": None,
    "submit_error": None,
    "chat_input": "",
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Create session on first load
if not st.session_state.session_id:
    try:
        r = requests.post(
            f"{st.session_state.api_host}/session", timeout=6
        )
        if r.ok:
            st.session_state.session_id = r.json()["session_id"]
        else:
            st.session_state.session_id = str(uuid.uuid4())
    except Exception:
        st.session_state.session_id = str(uuid.uuid4())

# ── API helpers ────────────────────────────────────────────────────────────────
def _sid() -> str:
    return st.session_state.session_id or ""

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
    return data is not None and data.get("status") == "healthy"

# ── UI helpers ─────────────────────────────────────────────────────────────────
def notice(kind: str, title: str, body: str = "") -> None:
    st.markdown(
        f"<div class='notice notice-{kind}'><div class='notice-title'>{title}</div>"
        + (f"<div style='margin-top:2px'>{body}</div>" if body else "") + "</div>",
        unsafe_allow_html=True,
    )

def badge_html(status: str) -> str:
    labels = {"running": "Running", "complete": "Complete", "failed": "Failed", "awaiting_human": "Needs review"}
    classes = {"running": "badge-running", "complete": "badge-complete", "failed": "badge-failed", "awaiting_human": "badge-awaiting"}
    return f"<span class='badge {classes.get(status, 'badge-offline')}'>{labels.get(status, status.title())}</span>"

def stat_block_html(value: str, label: str) -> str:
    return f"<div class='stat-block'><div class='stat-val'>{value}</div><div class='stat-label'>{label}</div></div>"

def bar_row_html(label: str, value: str, pct: float, color: str = "blue") -> str:
    return (f"<div style='margin-bottom:11px'><div style='display:flex;justify-content:space-between;font-size:0.78rem'>"
            f"<span style='color:#8a9bbf'>{label}</span><span style='color:#3a5070'>{value}</span></div>"
            f"<div class='bar-track'><div class='bar-{color}' style='width:{min(pct*100,100):.0f}%'></div></div></div>")

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<div style='padding:4px 0 24px'><div class='wordmark'>Nexus<span>.</span></div>"
                "<div style='font-size:0.68rem;color:#2a3a50;margin-top:4px;letter-spacing:0.08em;text-transform:uppercase'>Multi-Agent AI</div></div>",
                unsafe_allow_html=True)

    st.markdown("<div class='section-label'>API Host</div>", unsafe_allow_html=True)
    host_input = st.text_input("host", value=st.session_state.api_host, label_visibility="collapsed")
    st.session_state.api_host = host_input.rstrip("/")

    healthy = check_health()
    st.markdown(
        f"<div style='margin:6px 0 20px'><span class='badge {'badge-online' if healthy else 'badge-offline'}'>"
        f"{'Connected' if healthy else 'Offline'}</span></div>",
        unsafe_allow_html=True,
    )
    if not healthy:
        st.markdown("<div style='font-size:0.75rem;color:#2a3a50;line-height:1.55;margin-bottom:16px'>Cannot reach the server.</div>", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<div class='section-label'>System</div>", unsafe_allow_html=True)
    metrics, _ = api_get("/metrics")
    if metrics:
        c1, c2 = st.columns(2)
        c1.markdown(stat_block_html(str(metrics.get("total_tasks", 0)), "Tasks"), unsafe_allow_html=True)
        c2.markdown(stat_block_html(f"{metrics.get('task_success_rate', 0):.0%}", "Success"), unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:0.76rem;line-height:2.1;color:#3a5070;margin-top:10px'>"
                    f"Avg time &nbsp;<span style='color:#5a7a9a'>{metrics.get('avg_latency_s',0):.1f}s</span><br>"
                    f"Tokens &nbsp;&nbsp;&nbsp;<span style='color:#5a7a9a'>{metrics.get('total_tokens_used',0):,}</span></div>",
                    unsafe_allow_html=True)
    else:
        st.markdown("<div style='font-size:0.76rem;color:#2a3a50'>No data yet.</div>", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<div class='section-label'>Your Tasks</div>", unsafe_allow_html=True)

    # Load only THIS session's tasks
    my_tasks_data, _ = api_get(f"/session/{_sid()}/tasks")
    my_tasks = my_tasks_data.get("tasks", []) if my_tasks_data else []
    if my_tasks:
        for t in list(reversed(my_tasks))[:6]:
            preview = t.get("task", "")[:36] + ("…" if len(t.get("task", "")) > 36 else "")
            if st.button(preview, key=f"side_{t['task_id']}", use_container_width=True):
                st.session_state.task_id = t["task_id"]
                st.session_state.result = None
                st.rerun()
    else:
        st.markdown("<div style='font-size:0.76rem;color:#2a3a50'>No tasks yet.</div>", unsafe_allow_html=True)

# ── Main ───────────────────────────────────────────────────────────────────────
st.markdown("<div style='margin-bottom:30px'><div class='page-title'>Agent Workspace</div>"
            "<div class='page-subtitle'>Submit a task, monitor the pipeline, review the report, and ask follow-up questions.</div></div>",
            unsafe_allow_html=True)

tab_run, tab_monitor, tab_results, tab_chat, tab_history = st.tabs(
    ["New Task", "Monitor", "Results", "Discuss", "History"]
)

# ══ TAB 1 — NEW TASK ══════════════════════════════════════════════════════════
with tab_run:
    col_form, col_steps = st.columns([3, 2], gap="large")
    with col_form:
        st.markdown("<div class='section-label'>Task</div>", unsafe_allow_html=True)
        example = st.selectbox("examples", ["Write your own…"] + list(EXAMPLE_TASKS.keys()), label_visibility="collapsed")
        prefill = EXAMPLE_TASKS.get(example, "")
        task_text = st.text_area("task", value=prefill or st.session_state.get("_task_draft", ""), height=160,
                                  placeholder="Describe what you want the system to research, analyse, and report on…",
                                  label_visibility="collapsed")
        if not prefill:
            st.session_state["_task_draft"] = task_text

        btn_col, char_col = st.columns([1, 1])
        with btn_col:
            run_clicked = st.button("Run task", use_container_width=True, disabled=not healthy)
        with char_col:
            st.markdown(f"<div style='font-size:0.71rem;color:#2a3a50;padding-top:10px;text-align:right'>{len(task_text)} chars</div>", unsafe_allow_html=True)

        if st.session_state.submit_error:
            notice("error", st.session_state.submit_error)
        if not healthy:
            notice("warn", "Server unreachable", "Verify the API host in the sidebar.")

        if run_clicked:
            st.session_state.submit_error = None
            if len(task_text.strip()) < 10:
                st.session_state.submit_error = "Please write a more detailed task description."
                st.rerun()
            else:
                with st.spinner("Submitting…"):
                    resp, err = api_post("/task", {"task": task_text.strip(), "session_id": _sid()})
                if err:
                    st.session_state.submit_error = err
                    st.rerun()
                else:
                    st.session_state.task_id = resp["task_id"]
                    st.session_state.result = None
                    st.session_state.log = []
                    st.session_state.start_time = time.time()
                    st.session_state.submit_error = None
                    notice("success", "Task submitted", "Switch to the Monitor tab.")
                    time.sleep(0.7)
                    st.rerun()

    with col_steps:
        st.markdown("<div class='section-label'>Pipeline overview</div>", unsafe_allow_html=True)
        for name, desc in AGENT_STEPS:
            st.markdown(f"<div class='step-row pending'><div class='step-dot pending'></div>"
                        f"<div><div class='step-name'>{name}</div><div class='step-desc'>{desc}</div></div></div>",
                        unsafe_allow_html=True)

# ══ TAB 2 — MONITOR ══════════════════════════════════════════════════════════
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

        status_data, status_err = api_get(f"/status/{task_id}?session_id={_sid()}")
        if status_err:
            notice("warn", "Status unavailable", status_err)
        elif status_data:
            wf_status    = status_data.get("workflow_status", "running")
            current_step = status_data.get("current_step", "")
            retry        = status_data.get("retry_count", 0)
            elapsed      = status_data.get("elapsed_s") or (time.time() - st.session_state.start_time if st.session_state.start_time else 0)
            curr_idx     = STEP_KEY_MAP.get(current_step, -1)

            st.markdown(f"<div style='display:flex;align-items:center;gap:14px;margin:10px 0 18px'>"
                        f"{badge_html(wf_status)}<span style='font-size:0.76rem;color:#3a5070'>{elapsed:.0f}s</span>"
                        + (f"<span style='font-size:0.76rem;color:#c09020'>Retry {retry} of 3</span>" if retry else "")
                        + "</div>", unsafe_allow_html=True)

            pct = (curr_idx + 1) / len(AGENT_STEPS) if wf_status == "running" and curr_idx >= 0 else (1.0 if wf_status == "complete" else 0.0)
            st.progress(min(pct, 1.0))
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

            pipe_col, info_col = st.columns([1, 1], gap="large")
            with pipe_col:
                st.markdown("<div class='section-label'>Steps</div>", unsafe_allow_html=True)
                for i, (name, desc) in enumerate(AGENT_STEPS):
                    if wf_status == "complete" or i < curr_idx: rc, dc = "done", "done"
                    elif i == curr_idx: rc, dc = "active", "active"
                    else: rc, dc = "pending", "pending"
                    st.markdown(f"<div class='step-row {rc}'><div class='step-dot {dc}'></div>"
                                f"<div><div class='step-name'>{name}</div><div class='step-desc'>{desc}</div></div></div>",
                                unsafe_allow_html=True)

            with info_col:
                subtasks = status_data.get("subtasks", [])
                if subtasks:
                    st.markdown("<div class='section-label'>Subtasks</div>", unsafe_allow_html=True)
                    for i, s in enumerate(subtasks):
                        done_s   = wf_status == "complete" or i < curr_idx
                        active_s = i == curr_idx and wf_status == "running"
                        color  = "#22c564" if done_s else ("#3d7eff" if active_s else "#1e2d42")
                        marker = "·" if done_s else ("›" if active_s else "·")
                        st.markdown(f"<div style='font-size:0.79rem;color:{color};padding:4px 0;display:flex;gap:8px'>"
                                    f"<span style='flex-shrink:0'>{marker}</span><span>{s}</span></div>", unsafe_allow_html=True)

            if status_data.get("human_confirmation_needed"):
                st.markdown("<hr>", unsafe_allow_html=True)
                notice("warn", "Review required", "The system paused before continuing. Provide guidance below or proceed.")
                feedback = st.text_input("Guidance for the agent (optional)", placeholder="e.g. Use more realistic data ranges")
                b1, b2, _ = st.columns([1, 1, 3])
                with b1:
                    if st.button("Continue", use_container_width=True):
                        _, err = api_post(f"/confirm/{task_id}", {"action": "proceed", "feedback": feedback or ""})
                        if err: notice("error", "Could not resume", err)
                        else: st.rerun()
                with b2:
                    if st.button("Stop task", use_container_width=True):
                        _, err = api_post(f"/confirm/{task_id}", {"action": "abort"})
                        if err: notice("error", "Could not stop", err)
                        else: st.rerun()

            if wf_status == "failed":
                notice("error", "Task did not complete", "The pipeline could not recover. Try again with a more specific description.")
            elif wf_status == "complete":
                notice("success", "Complete", "View the report in the Results tab, or ask questions in the Discuss tab.")

            if wf_status == "running":
                time.sleep(3)
                st.rerun()
            elif wf_status == "complete" and not st.session_state.result:
                st.session_state.result, _ = api_get(f"/result/{task_id}?session_id={_sid()}")

# ══ TAB 3 — RESULTS ══════════════════════════════════════════════════════════
with tab_results:
    task_id = st.session_state.task_id
    if not task_id:
        st.markdown("<div style='padding:48px 0;text-align:center;color:#2a3a50;font-size:0.88rem'>No task selected.</div>", unsafe_allow_html=True)
    else:
        result = st.session_state.result
        if not result:
            result, err = api_get(f"/result/{task_id}?session_id={_sid()}")
            if result: st.session_state.result = result
            elif err: notice("info", "Result not available yet", "The task may still be running.")

        if result:
            wf_status = result.get("status", "")
            if wf_status == "running":
                notice("info", "Still running", "Check the Monitor tab.")
            elif wf_status == "complete":
                report = result.get("report", "")
                if report:
                    st.markdown("<div class='section-label'>Report</div>", unsafe_allow_html=True)
                    with st.expander("Read full report", expanded=True):
                        st.markdown(report)

                    # Download buttons row
                    dl1, dl2, _ = st.columns([1, 1, 3])
                    with dl1:
                        # Word document download
                        docx_url = f"{st.session_state.api_host}/report/{task_id}/docx?session_id={_sid()}"
                        docx_bytes = fetch_image(docx_url)  # reuse fetch helper
                        if docx_bytes:
                            st.download_button(
                                "Download .docx",
                                data=docx_bytes,
                                file_name=f"report_{task_id[:8]}.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                key="dl_docx",
                            )
                        else:
                            st.caption("docx not ready yet")
                    with dl2:
                        st.download_button(
                            "Download .md",
                            data=report,
                            file_name=f"report_{task_id[:8]}.md",
                            mime="text/markdown",
                            key="dl_md",
                        )
                    st.markdown("<hr>", unsafe_allow_html=True)

                token_total  = sum(result.get("token_usage", {}).values())
                timing_total = sum(result.get("step_timings", {}).values())
                artifacts_n  = len(result.get("artifacts", []))
                sources_n    = len(result.get("sources", []))
                c1, c2, c3, c4 = st.columns(4)
                for col, val, lbl in [(c1, f"{token_total:,}", "Tokens"), (c2, f"{timing_total:.1f}s", "Time"),
                                       (c3, str(artifacts_n), "Files"), (c4, str(sources_n), "Sources")]:
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
                        st.markdown(f"<div style='font-size:0.78rem;padding:4px 0;word-break:break-all'>"
                                    f"<a href='{s}' target='_blank' style='color:#3d7eff;text-decoration:none'>{s}</a></div>",
                                    unsafe_allow_html=True)

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
                            st.download_button(f"Download {filename}", data=img_bytes, file_name=filename, mime="image/png", key=f"dl_{filename}")
                        else:
                            st.markdown(f"<div style='font-size:0.78rem;color:#2a3a50;padding:6px 0'>{filename} — not available</div>", unsafe_allow_html=True)

            elif wf_status == "failed":
                notice("error", "Task did not complete", "Try again with a more specific description.")
            elif wf_status == "awaiting_human":
                notice("warn", "Waiting for review", "Go to the Monitor tab.")

# ══ TAB 4 — DISCUSS ══════════════════════════════════════════════════════════
with tab_chat:
    task_id = st.session_state.task_id
    result  = st.session_state.result

    if not task_id or not result or result.get("status") != "complete":
        st.markdown("<div style='padding:48px 0;text-align:center;color:#2a3a50;font-size:0.88rem'>"
                    "Complete a task first, then come back here to ask questions about the report.</div>",
                    unsafe_allow_html=True)
    else:
        st.markdown("<div class='section-label'>Discuss the report</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.8rem;color:#3a5070;margin-bottom:16px'>"
                    "Ask questions, request clarifications, or ask for a new chart. "
                    "The model uses the report and research — no re-running the full pipeline.</div>",
                    unsafe_allow_html=True)

        # Load chat history from API
        history_data, _ = api_get(f"/chat/{task_id}/history?session_id={_sid()}")
        history = history_data.get("history", []) if history_data else []

        # Render conversation
        if history:
            st.markdown("<div class='chat-wrap'>", unsafe_allow_html=True)
            for msg in history:
                role    = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    st.markdown(f"<div class='chat-user'>{content}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='chat-assistant'>{content}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='font-size:0.82rem;color:#2a3a50;padding:16px 0'>No messages yet. Ask anything about the report.</div>",
                        unsafe_allow_html=True)

        # Suggested questions
        if not history:
            st.markdown("<div class='section-label' style='margin-top:16px'>Suggestions</div>", unsafe_allow_html=True)
            suggestions = [
                "What are the three most important findings?",
                "Can you create a pie chart of the regional breakdown?",
                "What does this mean for investors?",
                "Summarise the methodology in simple terms.",
            ]
            s_cols = st.columns(2)
            for i, sug in enumerate(suggestions):
                with s_cols[i % 2]:
                    if st.button(sug, key=f"sug_{i}", use_container_width=True):
                        st.session_state.chat_input = sug
                        st.rerun()

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        # Input
        chat_col, send_col = st.columns([5, 1])
        with chat_col:
            user_msg = st.text_input(
                "message",
                value=st.session_state.chat_input,
                placeholder="Ask a question or request a chart…",
                label_visibility="collapsed",
                key="chat_field",
            )
        with send_col:
            send_clicked = st.button("Send", use_container_width=True)

        if send_clicked and user_msg.strip():
            st.session_state.chat_input = ""
            with st.spinner("Thinking…"):
                resp, err = api_post(
                    f"/chat/{task_id}",
                    {"message": user_msg.strip(), "session_id": _sid()},
                    timeout=30,
                )
            if err:
                notice("error", "Could not send message", err)
            else:
                intent       = resp.get("intent", "chat")
                new_artifacts = resp.get("new_artifacts", [])

                # Show new charts immediately
                if new_artifacts:
                    for a in new_artifacts:
                        filename = Path(a).name
                        url = f"{st.session_state.api_host}/artifacts/{resp.get('task_id', task_id)}/{filename}"
                        img_bytes = fetch_image(url)
                        if img_bytes:
                            st.image(img_bytes, use_container_width=True)
                            st.download_button(f"Download {filename}", data=img_bytes, file_name=filename,
                                               mime="image/png", key=f"chat_dl_{filename}")

                # Refresh result to include new artifacts
                if new_artifacts:
                    st.session_state.result, _ = api_get(f"/result/{task_id}?session_id={_sid()}")

                st.rerun()

# ══ TAB 5 — HISTORY ══════════════════════════════════════════════════════════
with tab_history:
    hc, rc = st.columns([5, 1])
    with rc:
        if st.button("Refresh", use_container_width=True, key="hist_ref"):
            st.rerun()

    my_tasks_data, tasks_err = api_get(f"/session/{_sid()}/tasks")
    my_tasks = list(reversed(my_tasks_data.get("tasks", []))) if my_tasks_data else []

    if tasks_err:
        notice("warn", "Could not load history", tasks_err)
    elif my_tasks:
        st.markdown(f"<div style='font-size:0.76rem;color:#3a5070;margin-bottom:16px'>{len(my_tasks)} task{'s' if len(my_tasks)!=1 else ''}</div>",
                    unsafe_allow_html=True)
        for t in my_tasks:
            status  = t.get("status", "unknown")
            preview = t.get("task", "")[:110] + ("…" if len(t.get("task", "")) > 110 else "")
            tid     = t.get("task_id", "")
            sub     = t.get("subtasks", 0)
            ret     = t.get("retries", 0)
            rl, rr  = st.columns([6, 1])
            with rl:
                retry_str = f" · {ret} retr{'ies' if ret!=1 else 'y'}" if ret else ""
                st.markdown(f"<div class='card' style='margin-bottom:8px'>"
                            f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:8px'>"
                            f"{badge_html(status)}"
                            f"<span style='font-size:0.68rem;font-family:monospace;color:#2a3a50'>{tid[:8]}</span>"
                            f"<span style='font-size:0.68rem;color:#2a3a50;margin-left:auto'>{sub} subtask{'s' if sub!=1 else ''}{retry_str}</span>"
                            f"</div><div style='font-size:0.83rem;color:#8a9bbf;line-height:1.5'>{preview}</div></div>",
                            unsafe_allow_html=True)
            with rr:
                if st.button("Open", key=f"open_{tid}", use_container_width=True):
                    st.session_state.task_id = tid
                    st.session_state.result = None
                    st.rerun()
    else:
        st.markdown("<div style='padding:48px 0;text-align:center;color:#2a3a50;font-size:0.88rem'>No tasks yet.</div>",
                    unsafe_allow_html=True)
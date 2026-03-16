"""
Nexus — Autonomous Multi-Agent AI System
"""

import time
import uuid
from pathlib import Path

import requests
import streamlit as st

API_HOST = "https://nexus-production-ebd3.up.railway.app"

st.set_page_config(page_title="Nexus", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Inter:wght@300;400;500;600&display=swap');
*,*::before,*::after{box-sizing:border-box;}
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.stApp{background:#06090f;}
[data-testid="stSidebar"]{background:#09101a!important;border-right:1px solid rgba(255,255,255,0.06)!important;}
[data-testid="stSidebar"] *{color:#8a9bbf!important;}
.wordmark{font-family:'Syne',sans-serif;font-size:1.35rem;font-weight:800;color:#fff;letter-spacing:-0.03em;}
.wordmark span{color:#3d7eff;}
.page-title{font-family:'Syne',sans-serif;font-size:1.9rem;font-weight:700;color:#fff;letter-spacing:-0.04em;margin:0;}
.page-subtitle{font-size:0.87rem;color:#4a6080;margin-top:5px;}
.section-label{font-size:0.68rem;font-weight:600;color:#3a5070;text-transform:uppercase;letter-spacing:0.12em;margin-bottom:10px;}
.card{background:#0c1520;border:1px solid rgba(255,255,255,0.06);border-radius:12px;padding:20px 22px;}
.badge{display:inline-flex;align-items:center;gap:6px;padding:4px 11px;border-radius:20px;font-size:0.68rem;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;}
.badge::before{content:'';width:6px;height:6px;border-radius:50%;display:block;}
.badge-running{background:rgba(61,126,255,0.12);color:#3d7eff;border:1px solid rgba(61,126,255,0.25);}
.badge-running::before{background:#3d7eff;animation:blink 1.4s ease-in-out infinite;}
.badge-complete{background:rgba(34,197,100,0.1);color:#22c564;border:1px solid rgba(34,197,100,0.2);}
.badge-complete::before{background:#22c564;}
.badge-failed{background:rgba(255,72,72,0.1);color:#ff5858;border:1px solid rgba(255,72,72,0.2);}
.badge-failed::before{background:#ff5858;}
.badge-awaiting{background:rgba(251,191,36,0.1);color:#fbbf24;border:1px solid rgba(251,191,36,0.2);}
.badge-awaiting::before{background:#fbbf24;animation:blink 1.4s ease-in-out infinite;}
.badge-online{background:rgba(34,197,100,0.08);color:#22c564;border:1px solid rgba(34,197,100,0.15);}
.badge-online::before{background:#22c564;}
.badge-offline{background:rgba(255,255,255,0.05);color:#4a6080;border:1px solid rgba(255,255,255,0.08);}
.badge-offline::before{background:#4a6080;}
@keyframes blink{0%,100%{opacity:1;}50%{opacity:0.25;}}
.step-row{display:flex;align-items:center;gap:12px;padding:10px 14px;border-radius:8px;margin-bottom:4px;}
.step-row.done{background:rgba(34,197,100,0.05);}
.step-row.active{background:rgba(61,126,255,0.08);border:1px solid rgba(61,126,255,0.18);}
.step-row.pending{opacity:0.3;}
.step-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0;}
.step-dot.done{background:#22c564;}
.step-dot.active{background:#3d7eff;box-shadow:0 0 8px rgba(61,126,255,0.7);animation:blink 1.4s infinite;}
.step-dot.pending{background:#1e2d42;}
.step-name{font-size:0.82rem;font-weight:500;color:#c0d0e8;}
.step-desc{font-size:0.71rem;color:#3a5070;margin-top:1px;}
.notice{padding:14px 18px;border-radius:8px;font-size:0.84rem;line-height:1.55;margin-bottom:14px;}
.notice-warn{background:rgba(251,191,36,0.07);border:1px solid rgba(251,191,36,0.18);color:#d4a020;}
.notice-success{background:rgba(34,197,100,0.07);border:1px solid rgba(34,197,100,0.18);color:#1aaa54;}
.notice-error{background:rgba(255,72,72,0.07);border:1px solid rgba(255,72,72,0.18);color:#c04040;}
.notice-info{background:rgba(61,126,255,0.07);border:1px solid rgba(61,126,255,0.18);color:#5080c0;}
.notice-title{font-weight:600;margin-bottom:3px;}
/* Chat */
.chat-wrap{max-height:440px;overflow-y:auto;padding:4px 0;display:flex;flex-direction:column;gap:8px;}
.chat-user{background:rgba(61,126,255,0.12);border:1px solid rgba(61,126,255,0.2);border-radius:16px 16px 4px 16px;padding:12px 16px;font-size:0.88rem;color:#c8d8f0;max-width:80%;align-self:flex-end;word-break:break-word;}
.chat-assistant{background:#0c1520;border:1px solid rgba(255,255,255,0.07);border-radius:16px 16px 16px 4px;padding:12px 16px;font-size:0.88rem;color:#8aacce;max-width:85%;align-self:flex-start;word-break:break-word;line-height:1.6;}
.chat-empty{text-align:center;padding:40px 0;color:#2a3a50;font-size:0.84rem;}
div[data-testid="stButton"]>button{background:#3d7eff!important;color:#fff!important;border:none!important;border-radius:8px!important;font-family:'Inter',sans-serif!important;font-weight:600!important;font-size:0.84rem!important;padding:0.55rem 1.5rem!important;transition:all 0.15s ease!important;}
div[data-testid="stButton"]>button:hover{background:#2d6aef!important;transform:translateY(-1px)!important;box-shadow:0 6px 24px rgba(61,126,255,0.28)!important;}
textarea,.stTextInput input{background:#0c1520!important;color:#c0d0e8!important;border:1px solid rgba(255,255,255,0.08)!important;border-radius:8px!important;font-family:'Inter',sans-serif!important;font-size:0.9rem!important;}
[data-testid="stSelectbox"]>div>div{background:#0c1520!important;border:1px solid rgba(255,255,255,0.08)!important;border-radius:8px!important;color:#c0d0e8!important;}
button[data-baseweb="tab"]{font-family:'Inter',sans-serif!important;font-size:0.82rem!important;font-weight:500!important;color:#3a5070!important;}
button[data-baseweb="tab"][aria-selected="true"]{color:#c0d0e8!important;font-weight:600!important;}
[data-testid="stProgress"]>div>div{background:#3d7eff!important;border-radius:4px!important;}
[data-testid="stProgress"]>div{background:rgba(255,255,255,0.05)!important;border-radius:4px!important;}
[data-testid="stDownloadButton"]>button{background:transparent!important;color:#3d7eff!important;border:1px solid rgba(61,126,255,0.3)!important;border-radius:6px!important;font-size:0.8rem!important;padding:0.4rem 1.2rem!important;box-shadow:none!important;}
[data-testid="stDownloadButton"]>button:hover{background:rgba(61,126,255,0.07)!important;transform:none!important;box-shadow:none!important;}
.stExpander{border:1px solid rgba(255,255,255,0.06)!important;border-radius:8px!important;background:#0c1520!important;}
hr{border-color:rgba(255,255,255,0.05)!important;margin:22px 0!important;}
.block-container{padding-top:2.5rem!important;max-width:1280px!important;}
#MainMenu,footer,header{visibility:hidden;}
label{color:#3a5070!important;font-size:0.7rem!important;font-weight:600!important;text-transform:uppercase!important;letter-spacing:0.1em!important;}
[data-testid="stSidebar"] div[data-testid="stButton"]>button{background:transparent!important;color:#4a6080!important;border:1px solid rgba(255,255,255,0.05)!important;font-size:0.77rem!important;padding:0.38rem 0.8rem!important;font-weight:400!important;box-shadow:none!important;}
[data-testid="stSidebar"] div[data-testid="stButton"]>button:hover{background:rgba(61,126,255,0.07)!important;color:#8aacce!important;transform:none!important;box-shadow:none!important;}
</style>
""", unsafe_allow_html=True)

AGENT_STEPS = [
    ("Planner",    "Breaks the task into ordered subtasks"),
    ("Researcher", "Gathers background knowledge"),
    ("Coder",      "Generates Python analysis code"),
    ("Executor",   "Runs code in a secure sandbox"),
    ("Critic",     "Evaluates and validates the output"),
    ("Reporter",   "Compiles the final report"),
]
STEP_KEY_MAP = {"PlannerAgent":0,"ResearchAgent":1,"CoderAgent":2,"ExecutorAgent":3,"CriticAgent":4,"ReporterAgent":5}

EXAMPLE_TASKS = {
    "Solar energy trends":     "Research and analyse global solar energy capacity growth from 2010 to 2023, covering key regions (China, USA, Europe). Identify the top growth markets, key drivers, and write a structured report with insights.",
    "EV adoption analysis":    "Research electric vehicle adoption trends from 2018 to 2024. Analyse regional market share and growth rates. Identify the top three growth markets and key adoption drivers. Write a comprehensive report.",
    "E-commerce performance":  "Analyse e-commerce sales performance across product categories over the last 3 years. Identify growth trends, seasonal patterns, and top performers. Write an executive summary with recommendations.",
}

def _friendly_error(exc=None, status_code=None):
    if status_code == 403: return "You don't have access to this resource."
    if status_code == 404: return "The requested resource could not be found."
    if status_code == 422: return "The request was invalid. Please check your input."
    if status_code in (500,502,503,504): return "The server is temporarily unavailable. Please try again in 30 seconds."
    if exc:
        msg = str(exc).lower()
        if any(w in msg for w in ("connection","refused","unreachable","network")): return "Unable to reach the server."
        if "timeout" in msg: return "The request timed out. Please try again."
    return "Something went wrong. Please try again."

DEFAULTS = {
    "session_id": None, "task_id": None, "result": None,
    "start_time": None, "submit_error": None, "chat_input": "",
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Init session
if not st.session_state.session_id:
    try:
        r = requests.post(f"{API_HOST}/session", timeout=6)
        st.session_state.session_id = r.json()["session_id"] if r.ok else str(uuid.uuid4())
    except Exception:
        st.session_state.session_id = str(uuid.uuid4())

def _sid(): return st.session_state.session_id or ""

def api_get(path, timeout=8):
    try:
        r = requests.get(f"{API_HOST}{path}", timeout=timeout)
        return (r.json(), None) if r.ok else (None, _friendly_error(status_code=r.status_code))
    except Exception as e:
        return None, _friendly_error(exc=e)

def api_post(path, data, timeout=12):
    try:
        r = requests.post(f"{API_HOST}{path}", json=data, timeout=timeout)
        return (r.json(), None) if r.ok else (None, _friendly_error(status_code=r.status_code))
    except Exception as e:
        return None, _friendly_error(exc=e)

def fetch_bytes(url):
    try:
        r = requests.get(url, timeout=15)
        return r.content if r.ok else None
    except Exception:
        return None

def check_health():
    d, _ = api_get("/health", timeout=5)
    return d is not None and d.get("status") == "healthy"

def notice(kind, title, body=""):
    st.markdown(f"<div class='notice notice-{kind}'><div class='notice-title'>{title}</div>"
                + (f"<div style='margin-top:2px'>{body}</div>" if body else "") + "</div>",
                unsafe_allow_html=True)

def badge_html(status):
    labels = {"running":"Running","complete":"Complete","failed":"Failed","awaiting_human":"Needs review"}
    cls    = {"running":"badge-running","complete":"badge-complete","failed":"badge-failed","awaiting_human":"badge-awaiting"}
    return f"<span class='badge {cls.get(status,'badge-offline')}'>{labels.get(status,status.title())}</span>"

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<div style='padding:4px 0 24px'><div class='wordmark'>Nexus<span>.</span></div>"
                "<div style='font-size:0.68rem;color:#2a3a50;margin-top:4px;letter-spacing:0.08em;text-transform:uppercase'>Multi-Agent AI</div></div>",
                unsafe_allow_html=True)

    healthy = check_health()
    badge_cls = "badge-online" if healthy else "badge-offline"
    badge_lbl = "Connected" if healthy else "Offline"
    st.markdown(f"<div style='margin-bottom:20px'><span class='badge {badge_cls}'>{badge_lbl}</span></div>",
                unsafe_allow_html=True)
    if not healthy:
        st.markdown("<div style='font-size:0.75rem;color:#2a3a50;line-height:1.55;margin-bottom:16px'>Cannot reach the server.</div>",
                    unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<div class='section-label'>Your Tasks</div>", unsafe_allow_html=True)

    my_tasks_data, _ = api_get(f"/session/{_sid()}/tasks")
    my_tasks = my_tasks_data.get("tasks", []) if my_tasks_data else []
    if my_tasks:
        for t in list(reversed(my_tasks))[:6]:
            preview = t.get("task","")[:36] + ("…" if len(t.get("task",""))>36 else "")
            if st.button(preview, key=f"side_{t['task_id']}", use_container_width=True):
                st.session_state.task_id = t["task_id"]
                st.session_state.result = None
                st.rerun()
    else:
        st.markdown("<div style='font-size:0.76rem;color:#2a3a50'>No tasks yet.</div>", unsafe_allow_html=True)

# ── Main ───────────────────────────────────────────────────────────────────────
st.markdown("<div style='margin-bottom:30px'><div class='page-title'>Agent Workspace</div>"
            "<div class='page-subtitle'>Submit a task, watch the pipeline run, read the report, and ask follow-up questions.</div></div>",
            unsafe_allow_html=True)

tab_run, tab_monitor, tab_results, tab_downloads, tab_chat, tab_history = st.tabs(
    ["New Task", "Monitor", "Results", "Downloads", "Discuss", "History"]
)

# ══ NEW TASK ══════════════════════════════════════════════════════════════════
with tab_run:
    col_form, col_steps = st.columns([3, 2], gap="large")
    with col_form:
        st.markdown("<div class='section-label'>Task</div>", unsafe_allow_html=True)
        example = st.selectbox("ex", ["Write your own…"]+list(EXAMPLE_TASKS.keys()), label_visibility="collapsed")
        prefill = EXAMPLE_TASKS.get(example, "")
        task_text = st.text_area("task", value=prefill or st.session_state.get("_draft",""),
                                  height=160, placeholder="Describe what you want the system to research and report on…",
                                  label_visibility="collapsed")
        if not prefill: st.session_state["_draft"] = task_text

        bc, cc = st.columns([1,1])
        with bc: run_clicked = st.button("Run task", use_container_width=True, disabled=not healthy)
        with cc: st.markdown(f"<div style='font-size:0.71rem;color:#2a3a50;padding-top:10px;text-align:right'>{len(task_text)} chars</div>", unsafe_allow_html=True)

        if st.session_state.submit_error: notice("error", st.session_state.submit_error)
        if not healthy: notice("warn", "Server unreachable", "The API is offline. Please try again shortly.")

        if run_clicked:
            st.session_state.submit_error = None
            if len(task_text.strip()) < 10:
                st.session_state.submit_error = "Please write a more detailed task description."
                st.rerun()
            else:
                with st.spinner("Submitting…"):
                    resp, err = api_post("/task", {"task": task_text.strip(), "session_id": _sid()})
                if err:
                    st.session_state.submit_error = err; st.rerun()
                else:
                    st.session_state.task_id = resp["task_id"]
                    st.session_state.result = None
                    st.session_state.start_time = time.time()
                    st.session_state.submit_error = None
                    notice("success", "Task submitted", "Switch to the Monitor tab to follow progress.")
                    time.sleep(0.6); st.rerun()

    with col_steps:
        st.markdown("<div class='section-label'>Pipeline</div>", unsafe_allow_html=True)
        for name, desc in AGENT_STEPS:
            st.markdown(f"<div class='step-row pending'><div class='step-dot pending'></div>"
                        f"<div><div class='step-name'>{name}</div><div class='step-desc'>{desc}</div></div></div>",
                        unsafe_allow_html=True)

# ══ MONITOR ══════════════════════════════════════════════════════════════════
with tab_monitor:
    if not st.session_state.task_id:
        st.markdown("<div style='padding:48px 0;text-align:center;color:#2a3a50;font-size:0.88rem'>Submit a task first.</div>", unsafe_allow_html=True)
    else:
        task_id = st.session_state.task_id
        h1, h2 = st.columns([5,1])
        with h1: st.markdown(f"<div style='font-size:0.72rem;color:#2a3a50;font-family:monospace'>ID: {task_id}</div>", unsafe_allow_html=True)
        with h2:
            if st.button("Refresh", use_container_width=True): st.rerun()

        sd, se = api_get(f"/status/{task_id}?session_id={_sid()}")
        if se: notice("warn","Status unavailable",se)
        elif sd:
            wf      = sd.get("workflow_status","running")
            step    = sd.get("current_step","")
            retry   = sd.get("retry_count",0)
            elapsed = sd.get("elapsed_s") or (time.time()-st.session_state.start_time if st.session_state.start_time else 0)
            cidx    = STEP_KEY_MAP.get(step,-1)

            st.markdown(f"<div style='display:flex;align-items:center;gap:14px;margin:10px 0 18px'>"
                        f"{badge_html(wf)}<span style='font-size:0.76rem;color:#3a5070'>{elapsed:.0f}s</span>"
                        +(f"<span style='font-size:0.76rem;color:#c09020'>Retry {retry} of 3</span>" if retry else "")
                        +"</div>", unsafe_allow_html=True)
            pct = (cidx+1)/len(AGENT_STEPS) if wf=="running" and cidx>=0 else (1.0 if wf=="complete" else 0.0)
            st.progress(min(pct,1.0))
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

            pc, ic = st.columns([1,1], gap="large")
            with pc:
                st.markdown("<div class='section-label'>Steps</div>", unsafe_allow_html=True)
                for i,(name,desc) in enumerate(AGENT_STEPS):
                    if wf=="complete" or i<cidx: rc,dc="done","done"
                    elif i==cidx: rc,dc="active","active"
                    else: rc,dc="pending","pending"
                    st.markdown(f"<div class='step-row {rc}'><div class='step-dot {dc}'></div>"
                                f"<div><div class='step-name'>{name}</div><div class='step-desc'>{desc}</div></div></div>",
                                unsafe_allow_html=True)
            with ic:
                subs = sd.get("subtasks",[])
                if subs:
                    st.markdown("<div class='section-label'>Subtasks</div>", unsafe_allow_html=True)
                    for i,s in enumerate(subs):
                        done_s = wf=="complete" or i<cidx
                        act_s  = i==cidx and wf=="running"
                        col = "#22c564" if done_s else ("#3d7eff" if act_s else "#1e2d42")
                        mk  = "·" if done_s else ("›" if act_s else "·")
                        st.markdown(f"<div style='font-size:0.79rem;color:{col};padding:4px 0;display:flex;gap:8px'>"
                                    f"<span style='flex-shrink:0'>{mk}</span><span>{s}</span></div>", unsafe_allow_html=True)

            if sd.get("human_confirmation_needed"):
                st.markdown("<hr>", unsafe_allow_html=True)
                notice("warn","Review required","The system paused. Provide guidance below or continue.")
                fb = st.text_input("Guidance (optional)", placeholder="e.g. Focus on the European market")
                b1,b2,_ = st.columns([1,1,3])
                with b1:
                    if st.button("Continue", use_container_width=True):
                        _,err = api_post(f"/confirm/{task_id}", {"action":"proceed","feedback":fb or ""})
                        if err: notice("error","Could not resume",err)
                        else: st.rerun()
                with b2:
                    if st.button("Stop task", use_container_width=True):
                        api_post(f"/confirm/{task_id}", {"action":"abort"})
                        st.rerun()

            if wf=="failed": notice("error","Task did not complete","Try again with a more specific description.")
            elif wf=="complete": notice("success","Complete","View the report in the Results tab.")

            if wf=="running": time.sleep(3); st.rerun()
            elif wf=="complete" and not st.session_state.result:
                st.session_state.result, _ = api_get(f"/result/{task_id}?session_id={_sid()}")

# ══ RESULTS ══════════════════════════════════════════════════════════════════
with tab_results:
    task_id = st.session_state.task_id
    if not task_id:
        st.markdown("<div style='padding:48px 0;text-align:center;color:#2a3a50;font-size:0.88rem'>No task selected.</div>", unsafe_allow_html=True)
    else:
        result = st.session_state.result
        if not result:
            result, err = api_get(f"/result/{task_id}?session_id={_sid()}")
            if result: st.session_state.result = result
            elif err: notice("info","Not available yet","The task may still be running.")

        if result:
            wf = result.get("status","")
            if wf=="running":
                notice("info","Still running","Check the Monitor tab.")
            elif wf=="complete":
                report = result.get("report","")
                if report:
                    st.markdown("<div class='section-label'>Report</div>", unsafe_allow_html=True)
                    with st.expander("Read full report", expanded=True):
                        st.markdown(report)
                    st.markdown("<hr>", unsafe_allow_html=True)

                # Charts
                artifacts = result.get("artifacts",[])
                images = [a for a in artifacts if Path(a).suffix.lower() in (".png",".jpg",".jpeg")]
                if images:
                    st.markdown("<div class='section-label'>Charts</div>", unsafe_allow_html=True)
                    for a in images:
                        filename = Path(a).name
                        url = f"{API_HOST}/artifacts/{task_id}/{filename}"
                        img = fetch_bytes(url)
                        if img:
                            st.image(img, use_container_width=True)

                sources = result.get("sources",[])
                if sources:
                    st.markdown("<hr>", unsafe_allow_html=True)
                    st.markdown("<div class='section-label'>Sources</div>", unsafe_allow_html=True)
                    for s in sources[:8]:
                        st.markdown(f"<div style='font-size:0.78rem;padding:4px 0;word-break:break-all'>"
                                    f"<a href='{s}' target='_blank' style='color:#3d7eff;text-decoration:none'>{s}</a></div>",
                                    unsafe_allow_html=True)

            elif wf=="failed":
                notice("error","Task did not complete","Try again with a more specific description.")
            elif wf=="awaiting_human":
                notice("warn","Waiting for review","Go to the Monitor tab.")

# ══ DOWNLOADS ════════════════════════════════════════════════════════════════
with tab_downloads:
    task_id = st.session_state.task_id
    result  = st.session_state.result

    if not task_id or not result or result.get("status") != "complete":
        st.markdown("<div style='padding:48px 0;text-align:center;color:#2a3a50;font-size:0.88rem'>"
                    "Complete a task to download the report.</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='section-label'>Download Report</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.82rem;color:#3a5070;margin-bottom:24px'>"
                    "Download your report in Word or PDF format, including all charts and analysis.</div>",
                    unsafe_allow_html=True)

        dc1, dc2, dc3 = st.columns([1,1,2])

        with dc1:
            st.markdown("<div class='card' style='text-align:center;padding:28px 20px'>", unsafe_allow_html=True)
            st.markdown("<div style='font-size:2rem;margin-bottom:8px'>📄</div>", unsafe_allow_html=True)
            st.markdown("<div style='font-weight:600;color:#c0d0e8;margin-bottom:4px'>Word Document</div>", unsafe_allow_html=True)
            st.markdown("<div style='font-size:0.76rem;color:#3a5070;margin-bottom:16px'>.docx — editable</div>", unsafe_allow_html=True)
            docx_url   = f"{API_HOST}/report/{task_id}/docx?session_id={_sid()}"
            docx_bytes = fetch_bytes(docx_url)
            if docx_bytes:
                st.download_button("Download .docx", data=docx_bytes,
                    file_name=f"report_{task_id[:8]}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True, key="dl_docx")
            else:
                st.caption("Not ready yet")
            st.markdown("</div>", unsafe_allow_html=True)

        with dc2:
            st.markdown("<div class='card' style='text-align:center;padding:28px 20px'>", unsafe_allow_html=True)
            st.markdown("<div style='font-size:2rem;margin-bottom:8px'>📋</div>", unsafe_allow_html=True)
            st.markdown("<div style='font-weight:600;color:#c0d0e8;margin-bottom:4px'>PDF</div>", unsafe_allow_html=True)
            st.markdown("<div style='font-size:0.76rem;color:#3a5070;margin-bottom:16px'>.pdf — print-ready</div>", unsafe_allow_html=True)
            pdf_url   = f"{API_HOST}/report/{task_id}/pdf?session_id={_sid()}"
            pdf_bytes = fetch_bytes(pdf_url)
            if pdf_bytes:
                st.download_button("Download .pdf", data=pdf_bytes,
                    file_name=f"report_{task_id[:8]}.pdf",
                    mime="application/pdf",
                    use_container_width=True, key="dl_pdf")
            else:
                st.caption("Not ready yet")
            st.markdown("</div>", unsafe_allow_html=True)

        # Also show charts available for download
        artifacts = result.get("artifacts",[])
        images = [a for a in artifacts if Path(a).suffix.lower() in (".png",".jpg",".jpeg")]
        if images:
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown("<div class='section-label'>Charts</div>", unsafe_allow_html=True)
            img_cols = st.columns(min(len(images), 3))
            for i, a in enumerate(images):
                filename = Path(a).name
                url = f"{API_HOST}/artifacts/{task_id}/{filename}"
                img = fetch_bytes(url)
                with img_cols[i % 3]:
                    if img:
                        st.image(img, use_container_width=True)
                        st.download_button(f"Download {filename}", data=img, file_name=filename,
                                           mime="image/png", key=f"chart_dl_{i}", use_container_width=True)

# ══ DISCUSS ══════════════════════════════════════════════════════════════════
with tab_chat:
    task_id = st.session_state.task_id
    result  = st.session_state.result

    if not task_id or not result or result.get("status") != "complete":
        st.markdown("<div style='padding:48px 0;text-align:center;color:#2a3a50;font-size:0.88rem'>"
                    "Complete a task first to discuss the report here.</div>", unsafe_allow_html=True)
    else:
        # Load history
        hd, _ = api_get(f"/chat/{task_id}/history?session_id={_sid()}")
        history = hd.get("history",[]) if hd else []

        # Render chat thread
        if history:
            st.markdown("<div class='chat-wrap'>", unsafe_allow_html=True)
            for msg in history:
                role    = msg.get("role","")
                content = msg.get("content","")
                cls     = "chat-user" if role=="user" else "chat-assistant"
                st.markdown(f"<div class='{cls}'>{content}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            # Suggested questions when chat is empty
            st.markdown("<div style='font-size:0.82rem;color:#3a5070;margin-bottom:20px'>"
                        "Ask questions about the report. The model uses your report and research — no re-running the pipeline.</div>",
                        unsafe_allow_html=True)
            st.markdown("<div class='section-label'>Try asking</div>", unsafe_allow_html=True)
            suggestions = [
                "What are the three most important findings?",
                "What does this mean for investors?",
                "Summarise the methodology in simple terms.",
                "What are the main risks or limitations?",
                "Create a bar chart comparing the top regions.",
                "What should I do with these insights?",
            ]
            sc = st.columns(2)
            for i, sug in enumerate(suggestions):
                with sc[i%2]:
                    if st.button(sug, key=f"sug_{i}", use_container_width=True):
                        st.session_state.chat_input = sug
                        st.rerun()

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        # Show any new charts from chat
        if "chat_new_images" in st.session_state and st.session_state.chat_new_images:
            for img_data in st.session_state.chat_new_images:
                st.image(img_data["bytes"], caption=img_data["name"], use_container_width=True)
                st.download_button(f"Download {img_data['name']}", data=img_data["bytes"],
                                   file_name=img_data["name"], mime="image/png",
                                   key=f"chat_img_{img_data['name']}")
            st.session_state.chat_new_images = []

        # Input row
        ci, si = st.columns([5,1])
        with ci:
            user_msg = st.text_input("msg", value=st.session_state.chat_input,
                                      placeholder="Ask a question about the report…",
                                      label_visibility="collapsed", key="chat_field")
        with si:
            send = st.button("Send", use_container_width=True)

        if send and user_msg.strip():
            st.session_state.chat_input = ""
            with st.spinner(""):
                resp, err = api_post(f"/chat/{task_id}",
                                     {"message": user_msg.strip(), "session_id": _sid()},
                                     timeout=35)
            if err:
                notice("error","Could not send message",err)
            else:
                new_arts = resp.get("new_artifacts",[])
                if new_arts:
                    imgs = []
                    for a in new_arts:
                        fn  = Path(a).name
                        url = f"{API_HOST}/artifacts/{task_id}/{fn}"
                        b   = fetch_bytes(url)
                        if b: imgs.append({"bytes":b,"name":fn})
                    st.session_state.chat_new_images = imgs
                    st.session_state.result, _ = api_get(f"/result/{task_id}?session_id={_sid()}")
                st.rerun()

# ══ HISTORY ══════════════════════════════════════════════════════════════════
with tab_history:
    _, rc = st.columns([5,1])
    with rc:
        if st.button("Refresh", use_container_width=True, key="hist_ref"): st.rerun()

    mtd, terr = api_get(f"/session/{_sid()}/tasks")
    mt = list(reversed(mtd.get("tasks",[]))) if mtd else []

    if terr: notice("warn","Could not load history",terr)
    elif mt:
        st.markdown(f"<div style='font-size:0.76rem;color:#3a5070;margin-bottom:16px'>{len(mt)} task{'s' if len(mt)!=1 else ''}</div>",
                    unsafe_allow_html=True)
        for t in mt:
            status  = t.get("status","unknown")
            preview = t.get("task","")[:110]+("…" if len(t.get("task",""))>110 else "")
            tid     = t.get("task_id","")
            rl,rr   = st.columns([6,1])
            with rl:
                st.markdown(f"<div class='card' style='margin-bottom:8px'>"
                            f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:8px'>"
                            f"{badge_html(status)}"
                            f"<span style='font-size:0.68rem;font-family:monospace;color:#2a3a50'>{tid[:8]}</span>"
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
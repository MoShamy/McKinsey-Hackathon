import json
import os
from io import BytesIO
from uuid import uuid4

import pandas as pd
import streamlit as st
from pypdf import PdfReader

# --- CUSTOM MODULES ---
from agent_logic import app
from create_ppt import generate_pptx

# ---- Custom CSS: Professional UI, No Emojis, Direct Form Styling ----
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&display=swap');
    
    :root {
        --navy: #0f172a;
        --navy-light: #1e293b;
        --slate: #64748b;
        --slate-light: #e2e8f0;
        --blue: #2563eb;
        --blue-bg: #eff6ff;
        --amber: #d97706;
        --amber-bg: #fffbeb;
        --emerald: #059669;
        --emerald-bg: #ecfdf5;
        --violet: #7c3aed;
        --violet-bg: #f5f3ff;
        --teal: #0d9488;
        --teal-bg: #f0fdfa;
        --white: #ffffff;
    }

    /* GLOBAL FONTS & BACKGROUND */
    html, body, [data-testid="stAppViewContainer"] { 
        font-family: 'DM Sans', system-ui, sans-serif; 
        background-color: #f8fafc;
        /* Subtle Dot Pattern */
        background-image: radial-gradient(#cbd5e1 1px, transparent 1px);
        background-size: 24px 24px;
    }
    
    .block-container { 
        padding-top: 2rem; 
        padding-bottom: 3rem; 
        max-width: 1200px; 
    }

    /* HEADER */
    .exec-header {
        text-align: center;
        margin-bottom: 2.5rem;
        padding: 2.5rem 1rem;
        background: linear-gradient(180deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.8) 100%);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255,255,255,0.6);
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.03);
    }
    .exec-header h1 { 
        color: var(--navy); 
        font-size: 2.2rem !important; 
        font-weight: 700 !important; 
        margin: 0 !important; 
        letter-spacing: -0.02em;
    }
    .exec-header p { 
        color: var(--slate); 
        font-size: 1.05rem !important; 
        margin: 0.6rem 0 0 0 !important; 
        font-weight: 400;
    }

    /* RUNNING BANNER */
    .running-banner {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.8rem;
        background: white;
        border: 1px solid var(--blue);
        border-radius: 12px;
        padding: 0.8rem 1.5rem;
        margin-bottom: 2rem;
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--blue);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.1);
    }
    .running-dot {
        width: 8px; height: 8px;
        background: var(--blue);
        border-radius: 50%;
        animation: pulse 1.2s ease-in-out infinite;
    }
    @keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.5; transform: scale(1.2); } }

    /* WORKFLOW STEPPER */
    .workflow-container {
        display: flex;
        justify-content: center;
        margin-bottom: 2.5rem;
    }
    .workflow-stepper { 
        display: inline-flex; 
        gap: 0.5rem; 
        background: white;
        padding: 0.5rem;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    }
    .workflow-step {
        padding: 0.4rem 1rem;
        border-radius: 8px;
        font-size: 0.85rem;
        font-weight: 600;
        transition: all 0.2s ease;
        border: 1px solid transparent;
        color: #94a3b8; /* Inactive text */
    }
    
    /* INACTIVE STATE */
    .workflow-step.inactive {
        background: #f8fafc;
        color: #cbd5e1;
    }

    /* ACTIVE STATES */
    .workflow-step.active.input { background: var(--slate-light); color: var(--navy); border-color: #cbd5e1; }
    .workflow-step.active.analyst { background: var(--blue-bg); color: var(--blue); border-color: var(--blue); }
    
    /* Both reviews use Amber */
    .workflow-step.active.human_review { background: var(--amber-bg); color: var(--amber); border-color: var(--amber); }
    .workflow-step.active.critique { background: var(--amber-bg); color: var(--amber); border-color: var(--amber); }
    
    .workflow-step.active.story_architect { background: var(--emerald-bg); color: var(--emerald); border-color: var(--emerald); }
    .workflow-step.active.done { background: var(--teal-bg); color: var(--teal); border-color: var(--teal); }

    .workflow-step.running { animation: stepRunning 1.5s ease-in-out infinite; }
    @keyframes stepRunning { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }

    /* PANELS & CARDS */
    .section-label {
        font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;
        color: var(--slate); margin-bottom: 0.8rem;
    }
    
    .agent-panel {
        background: rgba(255,255,255,0.8);
        backdrop-filter: blur(12px);
        border: 1px solid white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    }
    .empty-state {
        text-align: center; padding: 4rem 2rem;
        color: var(--slate); font-size: 0.95rem; line-height: 1.6;
    }
    .empty-state strong { color: var(--navy); }

    /* DIRECT FORM STYLING (Fixes the white bar issue) */
    [data-testid="stForm"] {
        background-color: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    }

    .feedback-cta {
        background: linear-gradient(90deg, var(--blue-bg) 0%, #fff 100%);
        border-left: 4px solid var(--blue);
        padding: 1rem 1.25rem;
        border-radius: 0 10px 10px 0;
        margin-bottom: 1rem;
        font-size: 0.9rem;
        color: var(--navy);
    }

    /* Hiding Streamlit details */
    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = f"streamlit_{uuid4().hex}"
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "snapshot" not in st.session_state:
        st.session_state.snapshot = None
    if "inputs" not in st.session_state:
        st.session_state.inputs = None
    if "pptx_bytes" not in st.session_state:
        st.session_state.pptx_bytes = None
    if "feedback_text" not in st.session_state:
        st.session_state.feedback_text = ""
    if "clear_feedback" not in st.session_state:
        st.session_state.clear_feedback = False
    if "pending_agent_run" not in st.session_state:
        st.session_state.pending_agent_run = None


def append_chat(role, content):
    st.session_state.chat_history.append({"role": role, "content": content})


def run_until_pause(inputs=None):
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    cursor = app.stream(inputs, config=config)
    for _ in cursor:
        pass
    st.session_state.snapshot = app.get_state(config)


def truncate_text(text, limit=12000):
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n[TRUNCATED]"


def read_uploaded_file(uploaded_file):
    name = uploaded_file.name
    suffix = os.path.splitext(name)[1].lower()
    data = uploaded_file.getvalue()

    if suffix == ".pdf":
        reader = PdfReader(BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)

    if suffix in {".csv"}:
        df = pd.read_csv(BytesIO(data))
        return df.to_csv(index=False)

    if suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(BytesIO(data))
        return df.to_csv(index=False)

    if suffix in {".txt", ".md"}:
        return data.decode("utf-8", errors="ignore")

    return f"Unsupported file type: {suffix}"


def render_workflow_stepper(snapshot, next_step, pending_agent_run=None):
    """
    Renders the stepper. Only the active step has color; others are grey.
    """
    steps = [
        ("Input", "input"),
        ("Analyst", "analyst"),
        ("Review Strategy", "human_review"),
        ("Slides", "story_architect"),
        ("Review Slides", "critique"),
        ("Export", "done"),
    ]
    
    current_active_id = "input"
    
    if pending_agent_run:
        current_active_id = pending_agent_run
    elif snapshot:
        if not snapshot.next:
            current_active_id = "done"
        else:
            current_active_id = next_step

    parts = []
    for name, sid in steps:
        cls = "workflow-step"
        is_active = (sid == current_active_id)
        
        if is_active:
            cls += f" active {sid}"
            if pending_agent_run and sid == pending_agent_run:
                cls += " running"
        else:
            cls += " inactive"
            
        parts.append(f'<span class="{cls}">{name}</span>')

    st.markdown(
        '<div class="workflow-container"><div class="workflow-stepper">' + "".join(parts) + "</div></div>",
        unsafe_allow_html=True,
    )


st.set_page_config(
    page_title="Executive Storytelling Copilot",
    layout="wide",
    initial_sidebar_state="collapsed",
)
init_session_state()

if not os.getenv("OPENAI_API_KEY"):
    st.warning("OPENAI_API_KEY is not set. Set it in .env or your environment to run the copilot.")

# ---- 1. Header (No Emojis) ----
st.markdown(
    """
    <div class="exec-header">
        <h1>Executive Storytelling Copilot</h1>
        <p>Turn unstructured data into executive-ready narratives and slides.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---- 2. Workflow Logic ----
snapshot = st.session_state.snapshot
next_step = snapshot.next[0] if snapshot and snapshot.next else None
if snapshot and not snapshot.next:
    next_step = "done"
pending_for_stepper = st.session_state.get("pending_agent_run")

render_workflow_stepper(snapshot, next_step, pending_agent_run=pending_for_stepper)

# ---- 3. Running Logic (Text Only) ----
if pending_for_stepper:
    agent_name = "Analyst" if pending_for_stepper == "analyst" else "Story Architect"
    
    st.markdown(
        f'<div class="running-banner">'
        f'<span class="running-dot"></span>'
        f'<span>{agent_name} is thinking...</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    
    run_inputs = st.session_state.inputs if pending_for_stepper == "analyst" else None
    run_until_pause(run_inputs)
    
    st.session_state.pending_agent_run = None
    st.rerun()

# ---- 4. Main Layout ----
left, right = st.columns([3, 2], gap="large")

# ========== LEFT COLUMN: Input + Feedback ==========
with left:
    # Removed the markdown wrapper div here that caused the white bar.
    # The form is now styled directly via CSS [data-testid="stForm"].
    
    with st.form("input_form"):
        user_request = st.text_input(
            "User goal — What deck do you need?",
            value="I need a deck for the Board on our proposed GCC residential expansion.",
            placeholder="e.g. Update the board on Q3 financials...",
        )
        uploaded_files = st.file_uploader(
            "Source files — Drop reports, data, emails here",
            type=["pdf", "csv", "xlsx", "xls", "txt", "md"],
            accept_multiple_files=True,
        )
        additional_notes = st.text_area(
            "Additional notes (optional)",
            value="",
            height=100,
            placeholder="Context, constraints, or specific tone requirements...",
        )
        
        st.write("") # Spacer
        
        col1, col2 = st.columns([1, 3])
        with col1:
            submitted = st.form_submit_button("Start Analysis", type="primary", use_container_width=True)

    if submitted:
        combined_sections = []
        if uploaded_files:
            for uploaded_file in uploaded_files:
                try:
                    content = read_uploaded_file(uploaded_file)
                except Exception as exc:
                    content = f"Failed to read file: {exc}"
                combined_sections.append(
                    f"FILE: {uploaded_file.name}\n{truncate_text(content)}"
                )
        if additional_notes.strip():
            combined_sections.append(f"NOTES:\n{additional_notes.strip()}")
        if not combined_sections:
            combined_sections.append("No files or notes were provided.")

        raw_files_content = "\n\n".join(combined_sections)
        st.session_state.inputs = {
            "user_request": user_request,
            "raw_files_content": raw_files_content,
        }
        append_chat("user", user_request)
        st.session_state.pending_agent_run = "analyst"
        st.rerun()

    # ---- Feedback Section ----
    if snapshot and next_step and next_step in ("human_review", "critique"):
        if st.session_state.clear_feedback:
            st.session_state.feedback_text = ""
            st.session_state.clear_feedback = False

        st.markdown("---")
        
        if next_step == "human_review":
            st.markdown(
                '<div class="feedback-cta"><strong>Review Strategy</strong><br/>'
                'Does the Analyst Report on the right look correct? Approve or edit below.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="feedback-cta"><strong>Review Slides</strong><br/>'
                'Check the slides on the right. If you want changes, the Critique agent will verify them.</div>',
                unsafe_allow_html=True,
            )

        feedback = st.text_area(
            "Your feedback",
            placeholder="Press 'Continue' to approve, or type instructions (e.g. 'Make it more aggressive', 'Add a slide on risks').",
            key="feedback_text",
            height=100,
        )
        
        if st.button("Continue Workflow", type="primary"):
            if feedback.strip() == "":
                feedback = "Proceed with this strategy."
            app.update_state(
                {"configurable": {"thread_id": st.session_state.thread_id}},
                {"human_feedback": feedback},
            )
            st.session_state.clear_feedback = True
            st.session_state.pending_agent_run = "story_architect"
            st.rerun()

    # ---- Export Section ----
    if snapshot and not snapshot.next:
        st.markdown("---")
        st.markdown('<div class="feedback-cta"><strong>Workflow Complete</strong></div>', unsafe_allow_html=True)
        
        col_dl, col_reset = st.columns([1, 1])
        with col_dl:
            # 1. Generate Button
            if st.button("Generate PowerPoint", type="primary", use_container_width=True):
                narrative_plan = snapshot.values.get("narrative_plan", {})
                
                # FIX: Call function without 'filename'. It returns a memory stream.
                pptx_stream = generate_pptx(narrative_plan) 
                
                # Store the bytes in session state
                st.session_state.pptx_bytes = pptx_stream.getvalue()
                st.rerun()
                
            # 2. Download Button (Only appears after generation)
            if st.session_state.pptx_bytes:
                st.download_button(
                    label="Download Final_Deck.pptx",
                    data=st.session_state.pptx_bytes,
                    file_name="Final_Deck.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    type="secondary",
                    use_container_width=True
                )
                
# ========== RIGHT COLUMN: Agent Outputs ==========
with right:
    st.markdown('<div class="section-label">Agent Intelligence</div>', unsafe_allow_html=True)

    if not snapshot:
        st.markdown(
            """
            <div class="agent-panel empty-state">
                <strong>Ready to assist</strong><br/><br/>
                Enter your goal and files on the left.<br/>
                I will analyze the strategy, then draft your slides.
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        analysis_report = snapshot.values.get("analysis_report")
        narrative_plan = snapshot.values.get("narrative_plan")
        current_step = snapshot.next[0] if snapshot.next else "done"
        critique_status = snapshot.values.get("next_step")

        # 1. Analyst Report
        with st.expander("Analyst Strategy Report", expanded=(current_step == "human_review" or current_step == "done")):
            if analysis_report:
                st.markdown(analysis_report)
            else:
                st.info("Waiting for Analyst...")

        # 2. Slide Plan
        with st.expander("Slide Plan (JSON)", expanded=(current_step == "critique" or current_step == "done")):
            if narrative_plan:
                st.code(json.dumps(narrative_plan, indent=2), language="json")
            else:
                st.info("Waiting for Story Architect...")

        # 3. Status
        with st.expander("System Status", expanded=False):
            st.write(f"**Step:** `{current_step}`")
            if critique_status:
                st.write(f"**Critique Decision:** `{critique_status}`")
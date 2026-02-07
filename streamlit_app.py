import json
import os
from io import BytesIO
from uuid import uuid4

import pandas as pd
import streamlit as st
from pypdf import PdfReader

from agent_logic import app
from create_ppt import generate_pptx

# --- HELPER: Display the plan professionally ---
def display_slide_plan(plan):
    """Renders the JSON slide plan as nice markdown."""
    slides = plan.get("slides", [])
    design = plan.get("design", {})
    
    if not slides:
        st.warning("No slides found in plan.")
        return

    # Show design choice nicely
    if design:
        st.caption(f"🎨 **Design Style determined by Agent:** Font: {design.get('font_family')}, Accent Color: {design.get('accent_color')}")

    for i, slide in enumerate(slides, 1):
        with st.expander(f"📄 Slide {i}: {slide.get('title', 'Untitled')}", expanded=True):
            # Title
            st.markdown(f"### {slide.get('title')}")
            
            # Bullets
            st.markdown("#### Content")
            for bullet in slide.get("bullets", []):
                st.markdown(f"- {bullet}")
                
            # Notes
            st.divider()
            st.markdown("#### 🗣️ Speaker Notes")
            st.caption(slide.get("speaker_notes", "No notes."))

# --- SETUP ---
def init_session_state():
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = f"streamlit_{uuid4().hex}"
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "snapshot" not in st.session_state:
        st.session_state.snapshot = None
    if "inputs" not in st.session_state:
        st.session_state.inputs = None
    # IMPORTANT: Keep track of the template file
    if "template_file" not in st.session_state:
        st.session_state.template_file = None

def append_chat(role, content):
    st.session_state.chat_history.append({"role": role, "content": content})

def run_until_pause(inputs=None):
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    try:
        cursor = app.stream(inputs, config=config)
        for _ in cursor:
            pass
        st.session_state.snapshot = app.get_state(config)
    except Exception as e:
        st.error(f"Workflow error: {e}")

def truncate_text(text, limit=12000):
    if len(text) <= limit: return text
    return text[:limit] + "\n\n[TRUNCATED]"

def read_uploaded_file(uploaded_file):
    name = uploaded_file.name
    suffix = os.path.splitext(name)[1].lower()
    data = uploaded_file.getvalue()
    if suffix == ".pdf":
        reader = PdfReader(BytesIO(data))
        return "\n".join([page.extract_text() or "" for page in reader.pages])
    if suffix in {".csv"}: return pd.read_csv(BytesIO(data)).to_csv(index=False)
    if suffix in {".xlsx", ".xls"}: return pd.read_excel(BytesIO(data)).to_csv(index=False)
    if suffix in {".txt", ".md"}: return data.decode("utf-8", errors="ignore")
    return f"Unsupported file type: {suffix}"

st.set_page_config(page_title="Executive Storytelling Copilot", layout="wide")
init_session_state()

if not os.getenv("OPENAI_API_KEY"):
    st.warning("OPENAI_API_KEY is not set.")
    st.stop()

# --- LAYOUT ---
left, right = st.columns([3, 2])

with left:
    st.title("Executive Storytelling Copilot")

    # 1. Chat History
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 2. Check Workflow State
    snapshot = st.session_state.snapshot
    next_step = snapshot.next[0] if snapshot and snapshot.next else None

    # 3. Input Form (Only show if not in middle of workflow)
    if not snapshot or not next_step:
        with st.form("input_form"):
            # --- SECTION 1: CONTEXT ---
            st.subheader("1. Context & Data")
            user_request = st.text_input("User goal", value="I need a deck for the Board explaining why we missed Q3 targets.")
            uploaded_files = st.file_uploader("Upload source files (PDF, Excel, CSV, Text)", type=["pdf", "csv", "xlsx", "xls", "txt", "md"], accept_multiple_files=True)
            additional_notes = st.text_area("Additional notes", height=100)

            st.divider() # Visual separation

            # --- SECTION 2: DESIGN ---
            st.subheader("2. Design (Optional)")
            st.caption("Upload your company template (.pptx) to use its branding. If skipped, the agent will design it.")
            uploaded_template = st.file_uploader("Upload PowerPoint Template", type=["pptx"], key="template_uploader")

            st.divider()
            submitted = st.form_submit_button("Start analysis", type="primary")

        if submitted:
            # A. Handle Template
            if uploaded_template:
                st.session_state.template_file = uploaded_template

            # B. Process Context Files
            combined_sections = []
            if uploaded_files:
                for uf in uploaded_files:
                    try: combined_sections.append(f"FILE: {uf.name}\n{truncate_text(read_uploaded_file(uf))}")
                    except Exception as e: st.error(f"Error reading {uf.name}: {e}")
            if additional_notes.strip():
                combined_sections.append(f"NOTES:\n{additional_notes.strip()}")
            
            raw_content = "\n\n".join(combined_sections) if combined_sections else "No files provided."
            
            # C. Start Agent
            st.session_state.inputs = {"user_request": user_request, "raw_files_content": raw_content}
            st.session_state.chat_history = [] # Reset chat
            append_chat("user", user_request)
            append_chat("assistant", "Analyzing inputs... please review the output on the right.")
            run_until_pause(st.session_state.inputs)
            st.rerun()

    # 4. Feedback Interface (Show when paused)
    if snapshot and next_step:
        if next_step == "human_review":
             st.info("⏸️ Workflow Paused: Please review the **Analyst Report** on the right.")
        elif next_step == "critique":
             st.info("⏸️ Workflow Paused: Please review the **Slide Plan** on the right.")
             
        with st.form("feedback_form"):
            feedback_text = st.text_area("Provide feedback to revise, or leave empty to approve:", height=100)
            decision = st.form_submit_button("Submit Decision")

        if decision:
            final_feedback = feedback_text if feedback_text.strip() != "" else "Proceed with this strategy."
            
            app.update_state(
                {"configurable": {"thread_id": st.session_state.thread_id}},
                {"human_feedback": final_feedback}
            )
            append_chat("assistant", f"✅ Feedback recorded: '{final_feedback}'. Continuing...")
            run_until_pause(None)
            st.rerun()

    # 5. Final Export Button
    if snapshot and not next_step:
        st.success("🎉 Workflow Complete!")
        narrative_plan = snapshot.values.get("narrative_plan", {})
        
        # Generate in memory
        try:
            # Get template from session state
            tmpl = st.session_state.get("template_file", None)
            if tmpl: tmpl.seek(0) # Safety reset

            pptx_file = generate_pptx(narrative_plan, template_file=tmpl)
            st.download_button(
                label="⬇️ Download PowerPoint Deck",
                data=pptx_file,
                file_name="Strategy_Deck.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
            )
        except Exception as e:
            st.error(f"Failed to generate PPTX: {e}")


# --- RIGHT COLUMN: AGENT OUTPUTS ---
with right:
    st.header("Agent Outputs")

    if snapshot:
        values = snapshot.values
        next_step = snapshot.next[0] if snapshot.next else None
        
        # Analyst Report Expander
        report_expanded = (next_step == "human_review")
        with st.expander("📑 Analyst Report (Strategy)", expanded=report_expanded):
            st.markdown(values.get("analysis_report", "*Pending analysis...*"))

        # Slide Plan Expander (The fixed part!)
        plan_expanded = (next_step == "critique" or next_step is None)
        with st.expander("🎞️ Slide Plan (Content & Design)", expanded=plan_expanded):
            narrative_plan = values.get("narrative_plan")
            if narrative_plan:
                # Shows the pretty markdown instead of ugly JSON
                display_slide_plan(narrative_plan)
            else:
                st.write("*Pending slide generation...*")
    else:
        st.info("Fill out the form on the left to start.")
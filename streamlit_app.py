import json
import os
from io import BytesIO
from uuid import uuid4

import pandas as pd
import streamlit as st
from pypdf import PdfReader

from agent_logic import app
from create_ppt import generate_pptx


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


st.set_page_config(page_title="Executive Storytelling Copilot", layout="wide")
init_session_state()

if not os.getenv("OPENAI_API_KEY"):
    st.warning("OPENAI_API_KEY is not set. The app will not run without it.")

left, right = st.columns([3, 2])

with left:
    st.title("Executive Storytelling Copilot")

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    with st.form("input_form"):
        user_request = st.text_input(
            "User goal",
            value="I need a deck for the Board explaining why we missed Q3 targets.",
        )
        uploaded_files = st.file_uploader(
            "Upload source files",
            type=["pdf", "csv", "xlsx", "xls", "txt", "md"],
            accept_multiple_files=True,
        )
        additional_notes = st.text_area(
            "Additional notes (optional)",
            value="",
            height=120,
        )
        submitted = st.form_submit_button("Start analysis")

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
        append_chat("assistant", "Analyzing inputs. Review the analyst report on the right.")
        run_until_pause(st.session_state.inputs)
        st.rerun()

    snapshot = st.session_state.snapshot
    next_step = None
    if snapshot and snapshot.next:
        next_step = snapshot.next[0]

    if snapshot and next_step:
        if st.session_state.clear_feedback:
            st.session_state.feedback_text = ""
            st.session_state.clear_feedback = False
        if next_step == "human_review":
            st.subheader("Review Analyst Report")
            st.caption("Add feedback to revise the analysis, or approve to proceed to slide creation.")
        elif next_step == "critique":
            st.subheader("Review Slide Plan")
            st.caption("Add feedback to revise the slides, or approve to finalize.")
        else:
            st.subheader("Continue")
        
        feedback = st.text_area(
            "Feedback",
            placeholder="Press Continue to approve, or type changes.",
            key="feedback_text",
        )
        if st.button("Continue workflow"):
            if feedback.strip() == "":
                feedback = "Proceed with this strategy."
            app.update_state(
                {"configurable": {"thread_id": st.session_state.thread_id}},
                {"human_feedback": feedback},
            )
            append_chat("assistant", f"Feedback recorded: {feedback}")
            st.session_state.clear_feedback = True
            run_until_pause(None)
            st.rerun()

    if snapshot and not snapshot.next:
        st.subheader("Export")
        if st.button("Generate PPTX"):
            narrative_plan = snapshot.values.get("narrative_plan", {})
            generate_pptx(narrative_plan, filename="Final_Deck.pptx")
            with open("Final_Deck.pptx", "rb") as handle:
                st.session_state.pptx_bytes = handle.read()
        if st.session_state.pptx_bytes:
            st.download_button(
                "Download PPTX",
                data=st.session_state.pptx_bytes,
                file_name="Final_Deck.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            )

with right:
    st.subheader("Agent Outputs")

    if snapshot:
        analysis_report = snapshot.values.get("analysis_report")
        narrative_plan = snapshot.values.get("narrative_plan")
        next_step = snapshot.next[0] if snapshot.next else "done"
        critique_status = snapshot.values.get("next_step")

        with st.expander("Analyst report", expanded=True):
            if analysis_report:
                st.markdown(analysis_report)
            else:
                st.write("No analyst report yet.")

        with st.expander("Narrative plan", expanded=True):
            if narrative_plan:
                st.code(json.dumps(narrative_plan, indent=2), language="json")
            else:
                st.write("No narrative plan yet.")

        with st.expander("Workflow status", expanded=True):
            st.write(f"Next step: {next_step}")
            if critique_status:
                st.write(f"Critique decision: {critique_status}")
    else:
        st.info("Start analysis to see agent outputs.")

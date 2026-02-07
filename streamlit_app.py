import json
import os
from io import BytesIO
from uuid import uuid4

import streamlit as st

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


def append_chat(role, content):
    st.session_state.chat_history.append({"role": role, "content": content})


def run_until_pause(inputs=None):
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    cursor = app.stream(inputs, config=config)
    for _ in cursor:
        pass
    st.session_state.snapshot = app.get_state(config)


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
        raw_files_content = st.text_area(
            "Paste source content",
            value=(
                "Metrics:\n"
                "Q3 Target: $10M | Q3 Actual: $8M\n"
                "churn_rate: 15% (Target 5%)\n"
                "Marketing Spend: $2M (On budget)\n"
                "Competitor Activity: High aggressive pricing in July."
            ),
            height=160,
        )
        submitted = st.form_submit_button("Start analysis")

    if submitted:
        st.session_state.inputs = {
            "user_request": user_request,
            "raw_files_content": raw_files_content,
        }
        append_chat("user", user_request)
        append_chat("assistant", "Analyzing inputs. Review the analyst report on the right.")
        run_until_pause(st.session_state.inputs)

    snapshot = st.session_state.snapshot
    next_step = None
    if snapshot and snapshot.next:
        next_step = snapshot.next[0]

    if snapshot and next_step:
        st.subheader("Continue")
        feedback = st.text_area("Feedback", placeholder="Press Continue to approve, or add changes.")
        if st.button("Continue workflow"):
            if feedback.strip() == "":
                feedback = "Proceed with this strategy."
            app.update_state(
                {"configurable": {"thread_id": st.session_state.thread_id}},
                {"human_feedback": feedback},
            )
            append_chat("assistant", f"Feedback recorded: {feedback}")
            run_until_pause(None)

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

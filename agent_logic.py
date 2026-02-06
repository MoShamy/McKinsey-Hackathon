import os
import json
from dotenv import load_dotenv
from typing import TypedDict, Optional

# --- IMPORTS ---
from langchain_openai import ChatOpenAI 
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# 1. Load the Secret Key
load_dotenv()

# 2. Define the State
class AgentState(TypedDict):
    raw_files_content: str
    user_request: str
    analysis_report: Optional[str]
    narrative_plan: Optional[dict]
    human_feedback: Optional[str]
    next_step: Optional[str]

# --- SETUP MODEL (Kept exactly as you requested) ---
llm = ChatOpenAI(
    model="gpt-4", 
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    openai_api_base=os.getenv("OPENAI_API_BASE"),
    temperature=0
)

# --- NODE 1: THE ANALYST ---
def analyst_node(state: AgentState):
    print("\n--- [1] ANALYST WORKING ---")
    combined_input = f"""
    USER GOAL: {state.get('user_request')}
    AVAILABLE FILE DATA: {state.get('raw_files_content')}
    """
    prompt = f"""
    You are a Senior Strategy Consultant. Analyze the User Goal and File Data.
    YOUR TASK:
    1. Identify the Core Strategy.
    2. GAPS: What is missing?
    3. RECOMMENDATION: Propose a clear narrative arc.
    Data Context: {combined_input}
    Keep it concise.
    """
    response = llm.invoke([
        SystemMessage(content="You are a strategic advisor."),
        HumanMessage(content=prompt)
    ])
    return {"analysis_report": response.content}

# --- NODE 2: THE STORY ARCHITECT ---
def story_node(state: AgentState):
    print("\n--- [2] STORY ARCHITECT WORKING ---")
    feedback = state.get('human_feedback', "No feedback provided.")
    
    prompt = f"""
    Create a 3-slide presentation plan based on this report:
    {state.get('analysis_report')}
    
    USER FEEDBACK TO ADDRESS: {feedback}
    
    CRITICAL: Return ONLY VALID JSON. Structure:
    {{
      "slides": [
         {{"title": "Title", "bullets": ["Pt1", "Pt2"], "speaker_notes": "Script"}}
      ]
    }}
    """
    response = llm.invoke([
        SystemMessage(content="You are a Presentation Expert. Output ONLY JSON."),
        HumanMessage(content=prompt)
    ])
    
    # Cleaning Logic
    content = response.content
    if "```" in content:
        content = content.split("```")[1].replace("json", "").strip()
    
    try:
        return {"narrative_plan": json.loads(content)}
    except:
        return {"narrative_plan": {"slides": [{"title": "Error", "bullets": ["JSON Failed"], "speaker_notes": "Retry"}]}}

# --- NODE 3: THE STRICT CRITIQUE ---
def critique_node(state: AgentState):
    print("\n--- [3] CRITIQUE WORKING ---")
    plan = state['narrative_plan']
    feedback = state.get('human_feedback', "No feedback provided.")

    # 1. FAIL SAFE
    if not plan.get("slides") or plan["slides"][0]["title"] == "Error":
         return {"next_step": "retry", "human_feedback": "JSON generation failed. Try again."}

    # 2. CHECK USER FEEDBACK (Strict Mode)
    if feedback and feedback != "Proceed with this strategy.":
        print(f"👀 VERIFYING FEEDBACK: '{feedback}'")
        validation_prompt = f"""
        User Feedback: "{feedback}"
        Proposed Slides: {json.dumps(plan['slides'])}
        
        Did the slides COMPLETELY solve the user's complaint? 
        If yes, say 'APPROVE'. 
        If no, say 'REJECT'.
        """
        review = llm.invoke([
            SystemMessage(content="You are a harsh Audit Officer."),
            HumanMessage(content=validation_prompt)
        ])
        
        if "REJECT" in review.content.upper():
            print(f"❌ CRITIQUE REJECTED: The slides didn't fully address '{feedback}'.")
            return {"next_step": "retry", "human_feedback": f"You failed to address: {feedback}. Be more specific."}

    # 3. GENERAL QUALITY CHECK
    print("✅ CRITIQUE APPROVED.")
    return {"next_step": "proceed"}

# --- BUILD WORKFLOW ---
workflow = StateGraph(AgentState)
workflow.add_node("analyst", analyst_node)
workflow.add_node("story_architect", story_node)
workflow.add_node("critique", critique_node)

workflow.set_entry_point("analyst")
workflow.add_edge("analyst", "story_architect")
workflow.add_edge("story_architect", "critique")

def should_continue(state):
    if state["next_step"] == "retry":
        return "story_architect"
    return END

workflow.add_conditional_edges("critique", should_continue, {"story_architect": "story_architect", END: END})

memory = MemorySaver()

# FINAL SETTING: Pauses before Story Architect AND before Critique
app = workflow.compile(checkpointer=memory, interrupt_before=["story_architect", "critique"])
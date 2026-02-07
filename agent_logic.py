import os
import json
from dotenv import load_dotenv
from typing import TypedDict, Optional, Literal
from langchain_openai import ChatOpenAI 
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

class AgentState(TypedDict):
    raw_files_content: str
    user_request: str
    analysis_report: Optional[str]
    narrative_plan: Optional[dict]
    human_feedback: Optional[str]
    design_style: Optional[dict] 

llm = ChatOpenAI(model="gpt-4o", temperature=0)

# --- 1. ANALYST NODE ---
def analyst_node(state: AgentState):
    feedback = state.get('human_feedback', '')
    combined_input = f"USER GOAL: {state.get('user_request')}\nDATA: {state.get('raw_files_content')}"
    
    prompt = f"""
    Analyze the User Goal and Data.
    1. Identify the Core Strategy.
    2. GAPS: What is missing?
    3. RECOMMENDATION: Propose a clear narrative arc.
    Context: {combined_input}
    Feedback: {feedback}
    """
    response = llm.invoke([
        SystemMessage(content="You are a strategic advisor."),
        HumanMessage(content=prompt)
    ])
    return {"analysis_report": response.content}

# --- 2. STORY ARCHITECT NODE ---
def story_node(state: AgentState):
    feedback = state.get('human_feedback', "No feedback provided.")
    print(f"--- ARCHITECT FEEDBACK RECEIVED: {feedback} ---") # Debug print
    
    prompt = f"""
    Based on this report: {state.get('analysis_report')}
    
    Current Feedback/Revision Request: "{feedback}"
    
    TASK 1: Create a 3-slide plan.
    TASK 2: Act as a CREATIVE DIRECTOR. Choose a font style.
    
    CRITICAL: Output ONLY VALID JSON.
    Structure:
    {{
      "design": {{
          "font_family": "Arial",
          "title_color": "#Hex",
          "accent_color": "#Hex"
      }},
      "slides": [
         {{"title": "Title", "bullets": ["Pt1", "Pt2"], "speaker_notes": "Script"}}
      ]
    }}
    """
    response = llm.invoke([
        SystemMessage(content="You are a Presentation Expert. Output ONLY JSON."),
        HumanMessage(content=prompt)
    ])
    
    content = response.content
    if "```" in content:
        content = content.split("```")[1].replace("json", "").strip()
    
    try:
        return {"narrative_plan": json.loads(content)}
    except:
        return {"narrative_plan": {"slides": [{"title": "Error", "bullets": ["JSON Error"], "speaker_notes": ""}]}}

# --- ROUTING LOGIC ---
def human_review_node(state: AgentState): return {}
def critique_node(state: AgentState): return {}

def route_after_review(state: AgentState):
    feedback = state.get('human_feedback', '')
    # If feedback is empty or generic approval, move forward
    if not feedback or feedback == "Proceed with this strategy.":
        return "story_architect"
    # Otherwise, go back to fix strategy
    return "analyst"

def route_after_critique(state: AgentState):
    feedback = state.get('human_feedback', '')
    # If feedback is empty or generic approval, FINISH
    if not feedback or feedback == "Proceed with this strategy.":
        return END
    # Otherwise, go back to fix slides
    return "story_architect"

# --- GRAPH SETUP ---
workflow = StateGraph(AgentState)
workflow.add_node("analyst", analyst_node)
workflow.add_node("human_review", human_review_node)
workflow.add_node("story_architect", story_node)
workflow.add_node("critique", critique_node)

workflow.set_entry_point("analyst")

workflow.add_edge("analyst", "human_review")
workflow.add_conditional_edges("human_review", route_after_review, {"analyst": "analyst", "story_architect": "story_architect"})

workflow.add_edge("story_architect", "critique")
# FIX: This was missing! Now it checks feedback before ending.
workflow.add_conditional_edges("critique", route_after_critique, {"story_architect": "story_architect", END: END})

memory = MemorySaver()
app = workflow.compile(checkpointer=memory, interrupt_before=["human_review", "critique"])
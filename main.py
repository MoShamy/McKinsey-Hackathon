import json
from agent_logic import app
from create_ppt import generate_pptx

# 1. SETUP INPUTS
user_chat = "I need a deck for the Board explaining why we missed Q3 targets."
file_content = """
Metrics:
Q3 Target: $10M | Q3 Actual: $8M
churn_rate: 15% (Target 5%)
Marketing Spend: $2M (On budget)
Competitor Activity: High aggressive pricing in July.
"""

config = {"configurable": {"thread_id": "interactive_mode_vFinal"}}
inputs = {"user_request": user_chat, "raw_files_content": file_content}

print("--- STARTING INTERACTIVE AGENT ---")
print("(Type 'quit' at any time to exit)")

# Start the workflow
cursor = app.stream(inputs, config=config)
resume_needed = False

while True:
    try:
        # A. Run until pause
        if resume_needed:
            cursor = app.stream(None, config=config)
        
        for event in cursor:
            pass # Just let it run to the next pause

    except Exception as e:
        print(f"Error: {e}")
        break

    # B. Check State
    snapshot = app.get_state(config)
    
    if not snapshot.next:
        print("\n🎉 WORKFLOW FINISHED!")
        final_state = snapshot.values
        if 'narrative_plan' in final_state:
            print("🔨 Generating PowerPoint...")
            generate_pptx(final_state['narrative_plan'], filename="Final_Deck.pptx")
        break

    # C. Show Context & Ask User
    current_step = snapshot.next[0]
    print(f"\n⏸️ PAUSED BEFORE: {current_step.upper()}")
    
    state_values = snapshot.values
    
    if current_step == "story_architect":
        print("\n🧐 ANALYST REPORT TO REVIEW:")
        print(state_values.get('analysis_report'))
        
    elif current_step == "critique":
        print("\n🧐 SLIDES TO REVIEW:")
        plan = state_values.get('narrative_plan', {})
        print(json.dumps(plan.get('slides', []), indent=2))

    # D. Input Loop
    user_feedback = input("\n👤 YOUR FEEDBACK (Press Enter to Approve, or type changes): ")
    
    if user_feedback.lower() in ["quit", "exit"]:
        break
    
    if user_feedback.strip() == "":
        user_feedback = "Proceed with this strategy."
        print("✅ Approved. Continuing...")
    else:
        print(f"📝 Feedback Recorded: {user_feedback}")

    # E. Update State & Resume
    app.update_state(config, {"human_feedback": user_feedback})
    resume_needed = True
    print("-" * 50)
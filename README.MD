# Agentic Executive Storytelling Copilot

### Overview

Client teams routinely start from messy, unstructured inputs (emails, spreadsheets, notes, PDFs) and must turn them into crisp, executive-ready narratives. This project is an **agentic, stateful, human-in-the-loop presentation copilot** that focuses on **reasoned executive storytelling**.

Instead of a single "make me a deck" prompt, we use a **LangGraph-powered multi-agent workflow** that acts as a strategy team: analyzing the core problem, drafting a narrative, and critiquing its own work before generating a native PowerPoint file.

### Problem Statement

- **High‑stakes audience**: Senior executives expect sharp, structured narratives, not raw summarization.
- **Unstructured inputs**: PDFs, CSVs, and loose notes must be synthesized into a single storyline.
- **Need for control**: Consultants must stay in the loop—approving strategy and refining the specific slide plan before export.

### Our Solution: A Stateful Multi‑Agent Workflow

We implement the system as a **stateful LangGraph machine** with explicit pause points for human-in-the-loop (HITL) control. The UI is built in **Streamlit**, featuring a professional split-pane interface (`Input` vs. `Agent Intelligence`).

#### The Architecture
1.  **Shared State (`AgentState`)**: The "Brain" that persists across the workflow. It holds the raw files, the analysis report, the slide plan, and the human feedback.
2.  **Orchestrator (LangGraph)**: Manages the lifecycle. It knows when to run, when to pause for input, and when to loop back for corrections.
3.  **Executor**: A dedicated Python module that converts the approved JSON plan into a native `.pptx` file.

### Detailed Agent Roles

The workflow consists of specialized "nodes" in the graph:

#### 1. The Analyst (Strategy Consultant)
* **Role**: Ignores slide formatting; focuses purely on business logic.
* **Action**: Ingests raw files and user goals. Produces a **Strategy Report** (Core Strategy, Gaps, Recommendation).
* **HITL**: The workflow **pauses** after this step. The user reviews the strategy text. If they reject it (e.g., "Too aggressive"), the Analyst re-runs.

#### 2. The Story Architect (Presentation Designer)
* **Role**: Converts the *approved* strategy into a concrete presentation structure.
* **Action**: Outputs a structured **Slide Plan** (Titles, Bullet points, Speaker Notes).
* **UI Representation**: The Streamlit app renders these as readable **Slide Cards**, allowing the user to scan the flow without reading raw JSON.

#### 3. The Critique (Audit Officer)
* **Role**: Quality control and validation.
* **Action**: It runs *after* the user reviews the slides. It checks:
    1.  Does the plan meet the user's original goal?
    2.  Did it incorporate the specific feedback the user just gave?
* **Looping**: If the Critique agent rejects the plan (e.g., "You missed the financial targets"), it forces a **Retry Loop** back to the Story Architect.

#### 4. The Executor (PPTX Generator)
* **Role**: Dumb execution.
* **Action**: Takes the final, approved JSON and uses `python-pptx` to generate a file.
* **Tech**: Handles text wrapping, font sizing, and layout assignment. Returns a byte stream for immediate download.

---

### System Workflow (End-to-End)

1.  **Input**: User uploads files (PDF, CSV, XLSX, MD) and defines a goal in Streamlit.
2.  **Analysis**: The **Analyst** agent runs.
3.  **Checkpoint 1 (Strategy)**: System pauses. User sees the "Analyst Report" on the right pane. User clicks "Continue" or provides feedback.
4.  **Drafting**: The **Story Architect** generates the slides.
5.  **Checkpoint 2 (Slides)**: System pauses. User sees "Slide Cards" (visual preview). User provides final tweaks (e.g., "Add a slide on risks").
6.  **Critique & Refinement**: The **Critique** agent validates the tweaks. If valid, the flow completes.
7.  **Export**: User clicks "Generate PowerPoint" to download `Final_Deck.pptx`.

---

### Repository Structure

| File | Purpose |
| :--- | :--- |
| `streamlit_app.py` | **The Frontend.** A professional UI with split layout (2:3 ratio). Handles file processing, state display (Slide Cards), and feedback collection. |
| `agent_logic.py` | **The Brain.** Defines `AgentState`, the LangGraph workflow, and the LLM prompts for Analyst, Architect, and Critique. |
| `create_ppt.py` | **The Hands.** Converts the JSON plan into a PowerPoint file using `python-pptx`. Includes fallback logic for text boxes. |
| `main.py` | **CLI Fallback.** A terminal-based version of the app for debugging or headless execution. |
| `requirements.txt` | Dependencies (`langgraph`, `streamlit`, `python-pptx`, `langchain-openai`, etc.). |

---

### Key Technical Features

* **Adaptive UI**: The Streamlit interface changes based on the agent state. It hides the input form once the workflow starts to focus the user on the Review/Feedback panels.
* **Resilient Parsing**: The `create_ppt.py` module includes a "Nuclear Option"—if a slide layout doesn't have a standard placeholder, it dynamically draws a text box to ensure content is never lost.
* **Memory Management**: Uses LangGraph's `MemorySaver` to maintain conversation history and state between Streamlit interactions.

---

### Quickstart

1.  **Clone and Install**
    ```bash
    git clone <REPO_URL>
    pip install -r requirements.txt
    ```

2.  **Set Environment Variables**
    Create a `.env` file:
    ```bash
    OPENAI_API_KEY=sk-...
    ```

3.  **Run the UI**
    ```bash
    streamlit run streamlit_app.py
    ```

4.  **Usage**
    * Upload a PDF or CSV (e.g., a financial report).
    * Type a goal: *"Create a Board Update based on these Q3 numbers."*
    * Follow the Agent's prompts to review and approve the strategy and slides.
    * Download the result.

---

### Evaluation Criteria Alignment

* **Agentic AI Design**: We demonstrate true autonomy through the **Critique** node, which can reject the Story Architect's work without human intervention if it detects a quality issue.
* **User Experience**: The split-pane UI transforms the "Black Box" of AI into a transparent "Glass Box," allowing users to see (and correct) the thinking process before the final output.
* **Practicality**: We solve the "Blank Page Problem" for consultants by getting them to a 80% draft in under 60 seconds.
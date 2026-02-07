## Agentic Executive Storytelling Copilot

### Overview

Client teams routinely start from messy, unstructured inputs (emails, spreadsheets, notes, images, spreadsheets, PDFs) and must turn them into crisp, executive-ready narratives. This project is an **agentic, stateful, human-in-the-loop presentation copilot** that focuses on **reasoned executive storytelling**.

Instead of a single "make me a deck" prompt, we use a **LangGraph-powered multi-agent workflow** that plans, critiques, and iterates on the narrative before writing slides and exporting a native PowerPoint file.

### Problem Statement

- **High‑stakes audience**: Senior executives expect sharp, structured narratives, not raw summarization.
- **Unstructured inputs**: PDFs, CSVs, notes, and emails must be synthesized into a single storyline.
- **Time pressure**: Teams need a strong first draft in minutes, with room for guided iteration.
- **Need for control**: Consultants must stay in the loop—approving, redirecting, and refining the AI’s thinking.

### Our Solution: A Stateful Multi‑Agent Storytelling System

We implement the system as a **stateful LangGraph workflow** with explicit pause points for human-in-the-loop (HITL) control:

- **Shared state (`AgentState`)**:  
  A single state object holds: `raw_files_content`, `user_request`, `analysis_report`, `narrative_plan`, `human_feedback`, and `next_step`. The application updates `human_feedback` when the user approves or requests changes, then resumes the graph.

- **Nodes in the graph**:
  - **Analyst**: Consumes `user_request` and `raw_files_content` (and optional `human_feedback` when re-run). Produces an **analysis report** (Core Strategy, Gaps, Recommendation)—no slides.
  - **Human_Review**: A passthrough node; the graph **interrupts before** it so the app can show the Analyst report and collect user approval or feedback.
  - **Story_Architect**: Consumes the approved `analysis_report` and any `human_feedback`. Produces a **narrative plan** (JSON: list of slides with `title`, `bullets`, `speaker_notes`).
  - **Critique**: Validates the narrative plan (e.g., JSON sanity, whether user feedback was addressed). Sets `next_step` to `"retry"` (loop back to Story_Architect) or continues to **END**. The graph **interrupts before** Critique so the user can review the slide plan and optionally add feedback.
  - **Executor** (outside the graph): After the workflow reaches END, the **application** calls `create_ppt.generate_pptx(narrative_plan)` to produce a native `.pptx` file. Currently uses the default `python-pptx` layout; support for a user-provided template is a natural extension.

The result is a **run → pause (review analysis) → run → pause (review slides) → run → optional retry or end → export PPTX** flow.

### Detailed Agent Roles (As Implemented)

- **Analyst** (`agent_logic.analyst_node`)
  - **Input**: `user_request`, `raw_files_content`; on re-runs, `human_feedback` is appended so the Analyst can revise.
  - **Task**: Act as a Senior Strategy Consultant. Output: (1) Core Strategy, (2) Gaps (what's missing), (3) Recommendation (narrative arc). Kept concise.
  - **Output**: `analysis_report` (plain text). `human_feedback` is cleared after use so the next pause can collect fresh input.
  - **HITL**: Workflow **interrupts before** `human_review`. The app shows the report and asks the user to approve ("Proceed with this strategy") or type feedback; feedback sends the graph back to the Analyst.

- **Human_Review** (`agent_logic.human_review_node`)
  - **Role**: Passthrough node; the graph **interrupts before** this node so the application can display state and prompt the user. No LLM call inside this node.
  - **Routing** (`route_after_review`): If `human_feedback` is empty or "Proceed with this strategy." → go to **Story_Architect**. Otherwise → go back to **Analyst** to incorporate feedback.

- **Story_Architect** (`agent_logic.story_node`)
  - **Input**: `analysis_report` and `human_feedback` (e.g., "Make it more aggressive", "Focus on risks").
  - **Task**: Create a 3-slide presentation plan; output **only** valid JSON.
  - **Output**: `narrative_plan` — a dict with key `"slides"`: list of `{ "title", "bullets", "speaker_notes" }`. If JSON parsing fails, a safe fallback structure is returned.
  - **HITL**: After Story_Architect runs, the graph **interrupts before** Critique. The app shows the slide plan; the user can approve or add feedback. That feedback is what Critique uses to decide if the slides "completely solve" the user's complaint (e.g., “shorter deck”, “more aggressive tone”, “focus on risks”).

- **Critique** (`agent_logic.critique_node`)
  - **Input**: `narrative_plan`, `human_feedback`.
  - **Behavior**: (1) **Fail-safe**: If no slides or first slide title is "Error", set `next_step = "retry"` and re-invoke Story_Architect. (2) **User feedback check**: If the user gave substantive feedback, an LLM validates whether the slides addressed it; if the LLM says **REJECT**, set `next_step = "retry"` and pass the reason back as `human_feedback`. (3) Otherwise set `next_step = "proceed"` and continue to END.
  - **HITL**: The user sees the slide plan at the pause *before* Critique and can type feedback; that feedback is what Critique uses for the REJECT/APPROVE check.

- **Executor** (`create_ppt.generate_pptx`)
  - **Invocation**: Not a graph node. Called by `main.py` or `streamlit_app.py` after the workflow reaches END and the user triggers export.
  - **Input**: `narrative_plan` (JSON with `slides`: title, bullets, speaker_notes), and optional filename (default `Strategy_Deck.pptx`).
  - **Task**: Create a `Presentation()`, add one slide per item using `slide_layouts[1]`, set title, bullets, and speaker notes. Save to disk.
  - **Output**: A native, editable `.pptx` file. User-provided template support is a planned extension.  

### Orchestrator & Control Logic (As Implemented)

Routing is implemented with two **conditional edges** in `agent_logic.py`:

- **After Human_Review** (`route_after_review`): Reads `human_feedback`. If empty or "Proceed with this strategy." → **Story_Architect**; else → **Analyst**.
- **After Critique** (`should_continue`): Reads `next_step`. If "retry" → **Story_Architect**; else → **END** (app then offers Generate PPTX).

Legacy description (conceptually accurate; implementation is the two edges above):
- **Role**: Decide which agent to call next based on:
  - Current state (what has been computed so far).
  - Human_Review decisions (approve / edit / reject).
  - Critique results (pass / fail with reasons).
- **Examples**:
  - If the user **dislikes the narrative** proposed by Story_Architect, Orchestrator re-invokes **Story_Architect** with new constraints (e.g., different audience, shorter deck, different tone).
  - If **Critique** flags weak “so what”, Orchestrator loops back to **Story_Architect** with Critique’s feedback injected into state.
  - If the user only wants to **update the template** (visuals) but keep the storyline, Orchestrator can skip directly to **Executor** with the new template.

This makes the system feel like a **controlled, agentic partner**: autonomous enough to plan and self-correct, but always steered by explicit human decisions at key checkpoints.

### Architecture: LangGraph State Machine (As Implemented)

- **State** (`AgentState` in `agent_logic.py`): `raw_files_content`, `user_request`, `analysis_report`, `narrative_plan`, `human_feedback`, `next_step`. All optional except the first two (provided at entry).

- **Graph structure**:
  1. **Entry** → **Analyst**.
  2. **Analyst** → **Human_Review** (edge).
  3. **Human_Review** → conditional: **Analyst** (if user gave feedback) or **Story_Architect** (if user approved).
  4. **Story_Architect** → **Critique** (edge).
  5. **Critique** → conditional: **Story_Architect** (if `next_step == "retry"`) or **END**.

- **Interrupts**: The compiled graph uses `interrupt_before=["human_review", "critique"]`. So execution stops *before* Human_Review (after Analyst) and *before* Critique (after Story_Architect). The driver (`main.py` or `streamlit_app.py`) calls `app.get_state(config)` to see which step is next, displays the relevant state to the user, collects `human_feedback`, calls `app.update_state(config, {"human_feedback": ...})`, then streams again with `app.stream(None, config)` to resume.

- **Executor**: Not in the graph. When the graph reaches END, the app calls `create_ppt.generate_pptx(snapshot.values["narrative_plan"], filename=...)` to write the `.pptx` file.

### System Workflow (End-to-End)

1. **User provides input**: A **user goal** (e.g., "I need a deck for the Board explaining why we missed Q3 targets") and **source content**. In the Streamlit app, content comes from uploaded files (PDF, CSV, XLSX, XLS, TXT, MD) plus optional notes; in the CLI (`main.py`) it can be inline text.
2. **Run to first interrupt**: The graph runs from **Analyst** → **Human_Review** and then **pauses** (because of `interrupt_before=["human_review", "critique"]`). The app shows the **Analyst report** and a feedback box.
3. **User at Human_Review**: User either approves (e.g., press Enter or type "Proceed with this strategy.") or types changes (e.g., "Focus on risks", "Audience is CEO"). The app calls `app.update_state(..., {"human_feedback": ...})` and resumes the graph. Routing sends execution either back to **Analyst** (if there was feedback) or to **Story_Architect** (if approved).
4. **Run to second interrupt**: **Story_Architect** produces `narrative_plan` (JSON slides). The graph then **pauses before Critique**. The app shows the **slide plan** (titles, bullets, speaker notes) and again asks for approval or feedback.
5. **User at Critique gate**: User approves or gives feedback. The app updates state and resumes. **Critique** runs: it may **REJECT** (e.g., slides did not address feedback or JSON failed) and set `next_step = "retry"`, sending the graph back to **Story_Architect**, or it sets `next_step = "proceed"` and the graph reaches **END**.
6. **Export**: When the graph has ended, the app shows an option to **Generate PPTX**. On click, it calls `create_ppt.generate_pptx(narrative_plan, filename="Final_Deck.pptx")`. The user can then download the file (Streamlit) or find it on disk (CLI).

### Repository Structure

| File / folder | Purpose |
|---------------|---------|
| `agent_logic.py` | Defines `AgentState`, LLM, and all graph nodes (Analyst, Human_Review, Story_Architect, Critique); builds the LangGraph workflow with conditional edges and `interrupt_before`; exports compiled `app` with `MemorySaver` checkpointer. |
| `create_ppt.py` | `generate_pptx(json_data, filename)` — builds a `python-pptx` presentation from the `narrative_plan` JSON (title, bullets, speaker notes per slide) and saves to disk. |
| `main.py` | CLI driver: sets initial `user_request` and `raw_files_content`, runs `app.stream()` in a loop, handles interrupts by printing state and reading user input from stdin, updates `human_feedback`, and calls `generate_pptx` when the workflow ends. |
| `streamlit_app.py` | Web UI: file upload (PDF, CSV, XLSX, XLS, TXT, MD), user goal and notes, run-until-pause logic, feedback form at each interrupt, and Export / Download PPTX when done. Displays Analyst report and Narrative plan in expanders. |
| `data/sample_input/` | Sample inputs for testing (e.g., GCC real estate market research, business plan, metrics CSV, internal email). |
| `.env` | `OPENAI_API_KEY` and optionally `OPENAI_API_BASE` for the LLM (see Quickstart). |

### Tech Stack

- **Language**: Python
- **Orchestration**: LangGraph (on top of LangChain); state checkpointing via `MemorySaver`
- **LLM**: OpenAI-compatible API (`ChatOpenAI` from `langchain_openai`); model `gpt-4`; configurable via `OPENAI_API_KEY` and `OPENAI_API_BASE` in `.env`
- **Presentation**: `python-pptx`; `create_ppt.generate_pptx` uses the default blank presentation and `slide_layouts[1]` per slide (user template support is a planned extension)
- **UI**: **Streamlit** (`streamlit_app.py`) for web; **CLI** (`main.py`) for terminal-driven runs
- **Inputs**: In Streamlit, supported file types are **PDF** (pypdf), **CSV**, **XLSX/XLS** (pandas, openpyxl), **TXT**, **MD**. Content is concatenated into `raw_files_content` and optionally truncated for context limits.

### Agentic & Business Metrics

We align system behavior with metrics that matter both technically and for consulting/judging.

#### 1. Agentic Metrics (Reasoning > Automation)

- **Critique "Save" Rate**
  - **Definition**: How often the Critique agent internally rejects weak drafts before the user sees them.
  - **Why it matters**: Shows the system has its own quality bar (not just "first response wins").

- **Feedback Loop Efficiency**
  - **Definition**: Number of conversation turns from "User Disagreement" to "User Approval".
  - **Target**: 1 turn when user says things like "Make it more aggressive" or "Retarget this to the CEO".

- **Context Retention**
  - **Definition**: Whether final slides correctly reference specific numbers from input files (e.g., Excel).
  - **Target**: 100% data integrity (no hallucinated client numbers).

#### 2. Operational Metrics (Speed & Function)

- **Time-to-First-Draft**
  - **Metric**: Time from file upload to first strategic analysis summary.
  - **Target**: Under 45 seconds.

- **End-to-End Generation Time**
  - **Metric**: From final approval to downloadable `.pptx`.
  - **Target**: Under 60 seconds for a ~5-slide deck.

- **Format Compliance**
  - **Metric**: Percentage of slides that follow the corporate template (fonts, colors, layouts).
  - **Target**: 100% template compliance.

#### 3. Storytelling Quality Metrics

- **Narrative Arc Detection**
  - **Test**: Can the system clearly identify the "villain" (problem) and "hero" (solution) from inputs?
  - **Success**: Slides follow a structured arc (e.g., *Situation → Complication → Resolution*) rather than a flat list of facts.

- **Speaker Note Depth**
  - **Test**: Are speaker notes just rephrasing bullets (fail) or adding talk‑track, nuance, and transitions (success)?
  - **Success**: At least 50% of speaker note content is not directly visible on the slide.

#### Summary Metrics Table

| Metric            | Target                             | Responsible Agent / Component |
|-------------------|------------------------------------|-------------------------------|
| Data Accuracy     | 100% match with CSV/PDF           | Analyst                       |
| Narrative Flow    | Clear problem–solution arc        | Story_Architect               |
| Self-Correction   | Catches generic/weak content      | Critique                      |
| Output Usability  | Fully native, editable `.pptx`    | Executor                      |
| User Latency      | \< 1 minute per interaction step  | Orchestrator (LangGraph)      |

### Quickstart

1. **Clone and install**

   ```bash
   git clone <REPO_URL>
   cd McKinsey-Hackathon
   pip install -r requirements.txt
   ```

2. **Configure environment**

   Create a `.env` file in the project root (or export variables):

   ```bash
   OPENAI_API_KEY=your_openai_api_key
   OPENAI_API_BASE=https://api.openai.com/v1   # optional; omit for default OpenAI
   ```

3. **Run the app**

   **Web UI (recommended):**

   ```bash
   streamlit run streamlit_app.py
   ```

   Then open the URL shown in the terminal. Use "User goal" and "Upload source files" (PDF, CSV, XLSX, TXT, MD, etc.), click "Start analysis", and follow the prompts to review the Analyst report and slide plan. When the workflow finishes, click "Generate PPTX" and "Download PPTX".

   **CLI (interactive):**

   ```bash
   python main.py
   ```

   Edit the `user_chat` and `file_content` variables at the top of `main.py` to change the scenario, or wire in file reading. The script will pause after the Analyst and after the Story_Architect; type your feedback or press Enter to approve. When done, the deck is written as `Final_Deck.pptx` in the current directory.

### Demo Script for Judges

To highlight the "agentic" nature of the system in a live demo:

- **Show the Conflict**
  - Intentionally generate a weak or generic narrative and display the **Critique** logs where the agent rejects it.
  - Narrate: **"Here the AI realized the slide was too generic and sent it back for a stronger ‘so what’."**

- **Show the Pivot**
  - Start with an audience like "Engineering Leadership", then mid-demo change it to "Group CEO".
  - Show how **Analyst** and **Story_Architect** update the strategic brief and slide plan to match the new audience.

- **Show the Native Output**
  - Open the generated `.pptx` in PowerPoint.
  - Click into a text box and edit it live to prove the deck is fully native and editable.

### Alignment with Hackathon Assessment Criteria

#### Problem Understanding, Framing & Innovation (25%)

- **Client problem & pain**: Strategy & Client Delivery teams must synthesize heterogeneous, often messy inputs (docs, data, screenshots) into **concise, executive-ready narratives** under time pressure.
- **Realistic scope**: We explicitly focus on the **storytelling and deck-generation layer** (from inputs → executive narrative → PPT), not full data warehousing or enterprise integration.
- **Innovation**: Instead of a single “make slides” call, we use a **stateful, multi-agent LangGraph design** with critique loops and human checkpoints to simulate how real teams think, argue, and converge on a storyline.
- **Clear agent goal**: Optimize for an **executive audience** by maximizing clarity of the “Big Idea”, preserving data integrity, and producing template-compliant, editable decks.

#### Agentic AI Solution Design (35%)

- **Autonomy with control**: The system independently:
  - Extracts and synthesizes insights (Analyst),
  - Designs slide flow (Story_Architect),
  - Self-critiques and revises (Critique),
  - Generates native PPTX (Executor),
  while still pausing for **Human_Review** at strategic points.
- **Reasoning flow**: The LangGraph DAG explicitly encodes decision points (e.g., Critique pass/fail, human approval/rejection) rather than burying them in a single prompt.
- **Handling ambiguity & edge cases**:
  - Conflicting inputs → Analyst highlights trade-offs instead of silently choosing.
  - Thin evidence → Critique can flag “insufficient support” and suggest clarifying questions for the user.
- **Explainability**:
  - Each agent writes **rationales into state** (e.g., “why this slide exists”, “why this draft was rejected”), which can be surfaced in the UI/logs to explain decisions to the user and the judges.

#### UI/UX Quality & Usability (15%)

- **User flow**: Intentionally simple: **Upload content → Review analysis → Approve narrative → Download PPTX**, with clear status indicators at each stage.
- **Decision transparency**: The UI surfaces:
  - Analyst’s strategic brief,
  - Story_Architect’s slide-by-slide rationale,
  - Critique’s comments when it rejects or amends a story.
- **Professional look & feel**: The user supplies their own corporate template; the Executor strictly adheres to that design, producing **visually consistent, executive-ready decks** out of the box.
- **Support for understanding agent decisions**: We treat rationales and critiques as first-class objects that can be inspected in the interface alongside the generated slides.

#### Pitch & Demo Quality (25%)

- **Storytelling structure for the pitch**:
  1. Problem: How teams currently struggle with unstructured inputs and manual slide crafting.
  2. Solution: Our agentic, HITL storytelling copilot.
  3. Impact: Faster time-to-first-draft, higher narrative quality, and template-compliant outputs.
- **Demo execution**:
  - Show the **full loop**: upload inputs → get a narrative → critique & revise → generate PPTX.
  - Deliberately trigger a **Critique “save”** to prove autonomous self-correction.
  - Change a key constraint mid-demo (e.g., change audience to “CEO”) and re-run.
- **Engagement & delivery**:
  - Use the metrics table and agent roles as talking points to explain *how* and *why* decisions are made.
  - Emphasize that the system behaves like a **junior consultant with a manager and partner built-in** (Analyst + Story_Architect + Critique + Human_Review).

### Why This Matters for Strategy & Client Delivery

- **From raw data to executive story**: Not just summarizing documents, but turning them into a storyline executives can act on.
- **Agentic behavior with control**: The system self-critiques and improves drafts while keeping the human in the loop at key checkpoints.
- **Production-ready outputs**: Native, template‑compliant PowerPoint decks that fit directly into client workflows.

This positions the solution as an **AI storytelling partner** for Strategy & Client Delivery teams—one that thinks, adapts, and produces, instead of simply formatting slides.


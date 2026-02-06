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

We design the system as a **stateful LangGraph DAG** rather than a simple linear chain:

- **The Brain (Shared State)**:  
  A central dictionary that holds uploaded content, analysis results, slide plans, critiques, human decisions, and user feedback as the conversation progresses.

- **Nodes (Agents) in the Graph**:
  - **Analyst**: Reads multi-format inputs (e.g., PDFs, Office docs, CSV/Excel, notes, screenshots/images\*) and extracts the *strategic insight* and context.  
    \*Videos are considered future work / stretch goal.
  - **Human_Review**: Pauses the graph, surfaces the analysis, and waits for **user approval / edits**.
  - **Story_Architect**: Designs the narrative arc and slide-by-slide flow.
  - **Critique**: Evaluates narrative quality; can **reject and loop back** to Story_Architect if the story is weak or generic.
  - **Executor**: Maps the final approved JSON story into a native, on‑brand `.pptx` using `python-pptx`, driven by a **user-provided template** (single or multiple layouts/backgrounds).

The result is a **conversation → confirm → execute → critique → loop** flow that feels like working with a junior consultant who can both think and produce.

### Detailed Agent Roles

- **Analyst (Strategist)**
  - **Input**: Raw documents (CSVs, PDFs, notes, emails, Office docs, and images where supported) + target audience (e.g., CEO vs. BU lead).
  - **Task**: Identify the *Big Idea*, key problems, levers, and recommended actions. Choose an appropriate narrative pattern (e.g., *Situation → Complication → Resolution*, *Problem → Agitation → Solution*, or *What → So What? → Now What?*).
  - **Output**: A **strategic brief (JSON)** capturing audience (with emphasis on executive needs), objective, narrative arc, key messages, and supporting data references.
  - **Human-in-the-loop expectation**: Analyst output is always surfaced for review; nothing proceeds to slides without explicit human approval.

- **Story_Architect (Storyboarder)**
  - **Input**: Strategic brief from Analyst (once approved by Human_Review).
  - **Task**: Decide slide order and purpose; for each slide, define title, key message, and why this slide exists in the story, optimized for an **executive audience** (concise, decision-oriented).
  - **Output**: **JSON slide plan** – a list of slides with titles, objectives, and reasoning for inclusion.
  - **Human-in-the-loop expectation**: User can accept, reorder, or reject the proposed narrative; rejections trigger a re-run with updated constraints (e.g., “shorter deck”, “more aggressive tone”, “focus on risks”).

- **Critique**
  - **Input**: Slide plan and (optionally) draft content.
  - **Task**: Act as a critical manager. Flag generic content, missing tension, weak "so what", or inconsistent data.  
  - **Behavior**: If quality is low, it **rejects** the draft and routes control back to Story_Architect with explicit improvement instructions.
  - **Human-in-the-loop expectation**: Critique rationales are displayed to the user so they can understand **why** the system changed the story before slides are regenerated.

- **Executor**
  - **Input**: Final, approved JSON story (slides + bullets + speaker notes) and a **user-supplied branded `.pptx` template** (single background or collection of layouts).
  - **Task**: Fill the template placeholders with titles, bullets, charts placeholders, and rich speaker notes while **strictly respecting template fonts, colors, and layout**.
  - **Output**: A real, fully editable PowerPoint file (`.pptx`) suitable for client delivery.
  - **Human-in-the-loop expectation**: User can download, inspect, and overwrite in PowerPoint; future iterations can re-use the same template with revised narratives.

- **Human_Review (Human-in-the-Loop)**
  - **Input**: Analyst output, Story_Architect plans, and/or Critique comments.
  - **Task**: Let the user:  
    - Approve or edit the strategic brief  
    - Change constraints (e.g., "Audience is now CEO", "Make tone more aggressive")  
    - Trigger a re-run of downstream agents with updated context  

### Orchestrator & Control Logic

On top of individual agents, we use an **Orchestrator** implemented via LangGraph routing logic:

- **Role**: Decide which agent to call next based on:
  - Current state (what has been computed so far).
  - Human_Review decisions (approve / edit / reject).
  - Critique results (pass / fail with reasons).
- **Examples**:
  - If the user **dislikes the narrative** proposed by Story_Architect, Orchestrator re-invokes **Story_Architect** with new constraints (e.g., different audience, shorter deck, different tone).
  - If **Critique** flags weak “so what”, Orchestrator loops back to **Story_Architect** with Critique’s feedback injected into state.
  - If the user only wants to **update the template** (visuals) but keep the storyline, Orchestrator can skip directly to **Executor** with the new template.

This makes the system feel like a **controlled, agentic partner**: autonomous enough to plan and self-correct, but always steered by explicit human decisions at key checkpoints.

### Architecture: LangGraph State Machine

We use **LangGraph** to model the system as a **state graph** with controlled loops and pauses:

- **State**: A Python dict containing:
  - `raw_inputs` (docs, CSVs, notes)
  - `strategic_brief`
  - `slide_plan`
  - `draft_slides`
  - `critiques`
  - `user_feedback`

- **Graph Flow (High level)**:
  1. `Analyst` → writes `strategic_brief`.
  2. `Human_Review` → user approves/edits or re-asks.
  3. `Story_Architect` → creates `slide_plan`.
  4. `Critique`:
     - If **failed**: add critique to state, route back to `Story_Architect`.
     - If **passed**: continue.
  5. `Executor` → generates `.pptx` from final JSON + template.

This graph-based design gives us:

- **Loops** (e.g., Critique → Story_Architect) without hacking prompt logic.
- **Pauses** (Human_Review) waiting for user confirmation.
- **Traceability**: Every intermediate state can be logged and shown in the demo.

### Tech Stack

- **Language**: Python
- **Orchestration**: LangGraph (on top of LangChain)
- **Models**: High-reasoning LLM (e.g., GPT‑4o, Claude 3.5 Sonnet)
- **Presentation Engine**: `python-pptx` with a corporate `.pptx` template
- **Inputs**: PDFs, notes, emails, screenshots/images (where supported), and structured data (e.g., CSV/Excel). Video understanding is considered out-of-scope for the current prototype but is a natural extension.

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

### Quickstart (Prototype)

> Note: Commands and filenames below reflect the intended prototype structure. Adjust as the implementation evolves.

1. **Clone the repository**

   ```bash
   git clone &lt;REPO_URL&gt;
   cd McKinsey-Hackathon
   ```

2. **Create environment & install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set API keys**

   ```bash
   export OPENAI_API_KEY=&lt;your_key&gt;      # or ANTHROPIC_API_KEY, depending on provider
   ```

4. **Place a corporate PowerPoint template**

   - Add your branded `.pptx` template to the `templates/` folder, e.g.:
     - `templates/corporate_mckinsey_style.pptx`

5. **Run the generator (example CLI)**

   ```bash
   python generator.py \
     --input data/sample_input/ \
     --template templates/corporate_mckinsey_style.pptx \
     --output output/executive_story_deck.pptx
   ```

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


# 🛡️ SecureLife Claims Processing Hub

An asynchronous, distributed AI agent pipeline for processing insurance claims. This project uses a modern two-tier architecture:
1. **Model Context Protocol (MCP) Server:** A remote data layer exposing SQLite database operations over `streamable_http`.
2. **LangGraph + Chainlit Client:** A conversational UI powered by a LangGraph multi-agent workflow that sanitizes inputs, evaluates fraud, verifies documents, and logs immutable audits via the MCP server.

---

## 📂 Project Structure

```text
SecureLife-MCP-Project/
│
├── securelife_client_app/
│   ├── __init__.py
│   ├── agent.py            # LangGraph multi-agent DAG pipeline logic
│   ├── app.py              # Chainlit WebSocket UI client implementation
│   ├── client_wrapper.py   # Model Context Protocol (MCP) client connection handling
│   └── guardrails.py       # Input/Output validation and content safety layers
│
├── SecureLife_claims.db    # Live SQLite database tracking claims records & audit logs
├── .gitignore              # Explicitly ignores secrets (.env), environments (venv/), and binary junk
├── README.md               # Master system documentation manual
├── chainlit.md             # Configuration and welcome page layout for Chainlit UI
└── requirements.txt        # Python package dependency tracking ledger

```

---

## 🏗️ System Architecture & Workflow

The core processing engine is built as a stateful, directed acyclic graph (DAG) controlled by a centralized `AgentState` paradigm. The workflow consists of 5 specialized processing nodes operating in a linear dependency chain:

```
[ User Input ] 
       │
       ▼
 ┌───────────┐      🛡️ Input Guardrails
 │  Triage   ├──────────────► (Validates user inputs & fetches records)
 └─────┬─────┘
       │
       ▼
 ┌───────────┐
 │DocVerifier├──────────────► (Heuristic completeness evaluation)
 └─────┬─────┘
       │
       ▼
 ┌───────────┐
 │FraudAnalyst├─────────────► (Algorithmic risk evaluation)
 └─────┬─────┘
       │
       ▼
 ┌───────────┐      🛡️ Output Guardrails
 │DeciderNode├──────────────► (GPT-4o adjudication & text sanitation)
 └─────┬─────┘
       │
       ▼
 ┌───────────┐
 │  Auditor  ├──────────────► (State updates via local MCP Server)
 └─────┬─────┘
       │
       ▼
[ Rendered UI ]     🎨 Real-time Markdown + Native JSON Audit Trails

```

### The 5-Node Graph Execution Lifecycle

1. **Triage Node**: Evaluates free-text user notes through an incoming safety guardrail pipeline. If clear, it uses the local MCP client connection to fetch the targeted master claim record.
2. **Document Verifier Node**: Connects to the document intelligence module via MCP to compute file completeness verification states.
3. **Fraud Analyst Node**: Executes data processing models via MCP to output a dynamic risk/fraud coefficient.
4. **Decision Maker Node**: Prompts `gpt-4o` with the compiled context matrix. It enforces structured heuristics (e.g., automated `REJECT` thresholds if fraud score $\ge 0.6$) and formats local currency tokens natively ($\text{₹}$ for INR amounts).
5. **Compliance Auditor Node**: Commits state transitions securely back to the SQLite relational database using server-side MCP tools, ensuring transactional data integrity.

---

## 🛠️ Tech Stack & Key Technologies

* **Orchestration**: `langgraph` (StateGraph workflow engine)
* **LLM Engine**: `langchain-openai` (utilizing the `gpt-4o` model framework)
* **Interface**: `chainlit` (Asynchronous UI with real-time process monitoring elements)
* **Tool Layer**: `Model Context Protocol (MCP)` via custom client wrappers
* **Database**: Embedded SQLite relational engine (`SecureLife_claims.db`)
* **Environment Configuration**: `python-dotenv`

---

## 📊 State Configuration Schema

The multi-agent execution pipeline maintains strict state isolation using a centralized structural schema:

```python
class AgentState(TypedDict):
    claim_id: str
    claim_record: dict
    doc_check: dict
    fraud: dict
    decision: dict        # Format: {"action": "APPROVE|REVIEW|REJECT", "reason": "..."}
    audit_result: dict
    user_note: Optional[str]

```

---

## 🚀 Quick Start & Installation

### Prerequisites

* macOS (Tested on MacBook Air architecture) or Linux Host (Ubuntu 24.04/26.04)
* Python 3.12 or higher
* Valid OpenAI API Private Secret Key

### 1. Repository Setup

Clone the workspace repository and navigate to the project root directory:

```bash
git clone [https://github.com/MAOFILHO/SecureLife-MCP-Project.git](https://github.com/MAOFILHO/SecureLife-MCP-Project.git)
cd SecureLife-MCP-Project

```

### 2. Virtual Environment Initialization

Create and activate an isolated Python runtime environment:

```bash
python3.12 -m venv venv
source venv/bin/activate

```

### 3. Dependencies Installation

Install the required application packages, graph frameworks, and runtime libraries:

```bash
pip install --upgrade pip
pip install -r requirements.txt

```

### 4. Inject Environment Secrets

Create a local configurations file inside the root repository framework:

```bash
cat << EOF > .env
OPENAI_API_KEY=sk-proj-YOUR_ACTUAL_API_SECRET_KEY_HERE
MCP_SERVER_URL=[http://127.0.0.1:8765](http://127.0.0.1:8765)
EOF

```

*(Note: `.env` is explicitly included in the system `.gitignore` file configuration to prevent private authorization exposures).*

---

## 🎮 Running the Application

To operate the end-to-end framework ecosystem, both the decentralized tools layer and UI layers must be brought online:

### Step A: Initialize the Model Context Protocol (MCP) Server

On the primary terminal window (with your virtual environment active), start your local resource provider or database orchestration layer:

```bash
# Example running command layout (Adjust depending on server execution script)
python -m securelife_mcp_server.server

```

### Step B: Launch the Chainlit UI Client Interface

Open a separate terminal workspace, spin up the front-facing user application:

```bash
python -m chainlit run securelife_client_app/app.py -w

```

The interface will automatically deploy in your default web browser at `http://localhost:8000`.

### Step C: Execute a Test Evaluation Pipeline

Type a query containing an active claim code pattern match inside the client chat box interface:

> *"Please run an automated check on file reference CLM-2025-0001 with high urgency."*

The system regex compiler will automatically isolate `CLM-2025-0001`, invoke the underlying LangGraph loop, append the secure database metrics audit trail, and render an interactive, collapsible JSON viewer natively in the UI window.

```
***

### How to apply this immediately:
1. Open your terminal on your Mac and type: `nano README.md`
2. Clear out any existing text.
3. Paste the markdown block above inside the editor.
4. Save and exit (`Ctrl + O`, `Enter`, `Ctrl + X`).
5. Run your final push commands:
   ```bash
   git add README.md
   git commit -m "Update README.md with complete project directory schema"
   git push origin main

```

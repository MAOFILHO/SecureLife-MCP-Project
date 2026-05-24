import os
import json
from typing import TypedDict, Optional
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

#from .client_wrapper import SecureLifeMCP
#from .guardrails import GuardrailPipeline
from securelife_client_app.client_wrapper import SecureLifeMCP
from securelife_client_app.guardrails import GuardrailPipeline


# Explicitly load local .env parameters from root workspace path
load_dotenv()

# Define structural state schema 
class AgentState(TypedDict):
    claim_id: str
    claim_record: dict
    doc_check: dict
    fraud: dict
    decision: dict        # Format: {"action": "APPROVE|REVIEW|REJECT", "reason": "..."}
    audit_result: dict
    user_note: Optional[str]

# Extract variables from environment with fallback defaults
SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8765")

# Initialize downstream dependencies
mcp_client = SecureLifeMCP(SERVER_URL)
guard = GuardrailPipeline(SERVER_URL)

llm = ChatOpenAI(model="gpt-4o")

decide_prompt = ChatPromptTemplate.from_template(
    "You are SecureLife's senior claims adjudicator. Decide ONE action: APPROVE, REVIEW, or REJECT.\n"
    "Heuristic guidance:\n"
    "- documents incomplete → REVIEW (request docs)\n"
    "- fraud_score ≥ 0.6 → REVIEW or REJECT (flag for senior review)\n"
    "- otherwise APPROVE\n\n"
    "Use ₹ for INR amounts when discussing claim_amount or sum_insured.\n\n"
    "Claim record: {record}\n"
    "Document check: {docs}\n"
    "Fraud analysis: {fraud}\n\n"
    "Return ONLY JSON: {{\\\"action\\\": \\\"APPROVE|REVIEW|REJECT\\\", \\\"reason\\\": \\\"≤ 1 sentence\\\"}}"
)
decide_chain = decide_prompt | llm

# --- Graph Nodes ---
def triage_node(state: AgentState) -> dict:
    note = state.get("user_note") or ""
    if note:
        ok, viols = guard.check_input(note)
        if not ok:
            return {
                "claim_record": {"error": "input blocked", "violations": viols},
                "decision": {"action": "BLOCKED", "reason": f"Input rejected by guardrails: {viols}"}
            }
    rec = mcp_client.fetch_claim(state["claim_id"])
    return {"claim_record": rec}

def doc_verifier_node(state: AgentState) -> dict:
    if state.get("decision", {}).get("action") == "BLOCKED":
        return {}
    docs = mcp_client.verify_documents(state["claim_id"])
    return {"doc_check": docs}

def fraud_analyst_node(state: AgentState) -> dict:
    if state.get("decision", {}).get("action") == "BLOCKED":
        return {}
    fraud = mcp_client.calculate_fraud_score(state["claim_id"])
    return {"fraud": fraud}

def decision_maker_node(state: AgentState) -> dict:
    if state.get("decision", {}).get("action") == "BLOCKED":
        return {}
    raw = decide_chain.invoke({
        "record": json.dumps(state["claim_record"]),
        "docs":   json.dumps(state["doc_check"]),
        "fraud":  json.dumps(state["fraud"])
    }).content.strip()
    
    if raw.startswith("```"):
        #raw = raw.split("```").replace("json", "").strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        d = json.loads(raw)
    except Exception:
        d = {"action": "REVIEW", "reason": "unparseable LLM output"}
    
    d["reason"] = guard.check_output(d.get("reason", ""))
    return {"decision": d}

def compliance_auditor_node(state: AgentState) -> dict:
    decision = state["decision"]
    if decision.get("action") == "BLOCKED":
        return {"audit_result": {"skipped": True, "reason": "blocked at triage"}}
    
    new_status = {"APPROVE": "APPROVED", "REVIEW": "UNDER_REVIEW",
                  "REJECT":  "REJECTED"}.get(decision["action"], "UNDER_REVIEW")
    
    res = mcp_client.update_claim_status(
        claim_id=state["claim_id"], 
        new_status=new_status,
        reason=decision.get("reason", ""), 
        actor="agent:claims_pipeline"
    )
    return {"audit_result": res}

# --- Graph Workflow Compilation Layout ---
workflow = StateGraph(AgentState)
workflow.add_node("triage",              triage_node)
workflow.add_node("doc_verifier",        doc_verifier_node)
workflow.add_node("fraud_analyst",       fraud_analyst_node)
workflow.add_node("decision_maker",      decision_maker_node)
workflow.add_node("compliance_auditor",  compliance_auditor_node)

workflow.set_entry_point("triage")
workflow.add_edge("triage",         "doc_verifier")
workflow.add_edge("doc_verifier",   "fraud_analyst")
workflow.add_edge("fraud_analyst",  "decision_maker")
workflow.add_edge("decision_maker", "compliance_auditor")
workflow.add_edge("compliance_auditor", END)

claims_agent = workflow.compile()
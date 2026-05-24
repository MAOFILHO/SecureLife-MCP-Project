import json
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from .client_wrapper import SecureLifeMCP
from .guardrails import GuardrailPipeline

class AgentState(TypedDict):
    claim_id: str
    claim_record: dict
    doc_check: dict
    fraud: dict
    decision: dict        # Format: {"action": "APPROVE|REVIEW|REJECT", "reason": "..."}
    audit_result: dict
    user_note: Optional[str]

# Connect interfaces across boundaries via streamable_http setup
mcp_client = SecureLifeMCP("http://127.0.0.1:8765")
guard = GuardrailPipeline("http://127.0.0.1:8765")

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

# --- Graphs Nodes Calling SecureLifeMCP Network Wrapper ---
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
        raw = raw.split("```").replace("json", "").strip()
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
        claim_id=state["claim_id"], new_status=new_status,
        reason=decision.get("reason", ""), actor="agent:claims_pipeline"
    )
    return {"audit_result": res}

# --- Build StateGraph Workflow Layout ---
graph = StateGraph(AgentState)
graph.add_node("triage",              triage_node)
graph.add_node("doc_verifier",        doc_verifier_node)
graph.add_node("fraud_analyst",       fraud_analyst_node)
graph.add_node("decision_maker",      decision_maker_node)
graph.add_node("compliance_auditor",  compliance_auditor_node)

graph.set_entry_point("triage")
graph.add_edge("triage",         "doc_verifier")
graph.add_edge("doc_verifier",   "fraud_analyst")
graph.add_edge("fraud_analyst",  "decision_maker")
graph.add_edge("decision_maker", "compliance_auditor")
graph.add_edge("compliance_auditor", END)

compiled_graph = graph.compile()
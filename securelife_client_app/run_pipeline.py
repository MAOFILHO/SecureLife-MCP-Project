import sys
from .pipeline import compiled_graph

def execute_run(claim_id: str, note: str = ""):
    print(f"\n🚀 Running Pipeline for Claim: {claim_id}")
    if note:
        print(f"🛡 Input Note Passed: '{note}'")
        
    state_input = {
        "claim_id": claim_id,
        "user_note": note,
        "claim_record": {},
        "doc_check": {},
        "fraud": {},
        "decision": {},
        "audit_result": {}
    }
    
    final_output = compiled_graph.invoke(state_input)
    
    print("\n" + "="*50)
    print("                PIPELINE EXECUTION BRIEF")
    print("="*50)
    print(f"Claim Reference:  {final_output.get('claim_id')}")
    print(f"Decision Status:  {final_output.get('decision', {}).get('action')}")
    print(f"Reasoning Logs:   {final_output.get('decision', {}).get('reason')}")
    print(f"Fraud Weight metrics: {final_output.get('fraud', {}).get('score')}")
    print(f"Audit Status Check:  {final_output.get('audit_result', {})}")
    print("="*50 + "\n")

if __name__ == "__main__":
    cid = sys.argv if len(sys.argv) > 1 else "CLM-2025-0002"
    user_note = sys.argv if len(sys.argv) > 2 else ""
    execute_run(cid, user_note)
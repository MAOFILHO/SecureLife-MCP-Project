import re
import chainlit as cl
#from .agent import claims_agent
from securelife_client_app.agent import claims_agent

# Regex to isolate Claim IDs out of any raw textual input
CLAIM_ID_PATTERN = re.compile(r"\bCLM-\d{4}-\d{4}\b", re.IGNORECASE)

@cl.on_chat_start
async def on_chat_start():
    welcome_msg = (
        "📊 **SecureLife Automated Claims Co-Pilot System Engine Running.**\n\n"
        "Provide a Claim Reference Number (e.g., `CLM-2025-0002`) to process a claim "
        "through the decoupled multi-agent verification flow."
    )
    await cl.Message(content=welcome_msg).send()

@cl.on_message
async def on_message(message: cl.Message):
    user_input = message.content.strip()
    
    # Extract structural references
    match = CLAIM_ID_PATTERN.search(user_input)
    if not match:
        await cl.Message(
            content="❌ **System Parsing Fault:** No matching claim pattern detected (`CLM-YYYY-XXXX`). Please re-verify."
        ).send()
        return

    claim_id = match.group(0).upper()
    user_note = user_input.replace(match.group(0), "").strip()

    async with cl.Step(name="Running LangGraph Process Pipeline") as step:
        step.input = f"Target Claim: {claim_id} | Note Parameter: '{user_note}'"
        
        state_input = {
            "claim_id": claim_id,
            "user_note": user_note,
            "claim_record": {},
            "doc_check": {},
            "fraud": {},
            "decision": {},
            "audit_result": {}
        }
        
        # Execute the fully decoupled agent pipeline asynchronously
        final_output = await cl.make_async(claims_agent.invoke)(state_input)
        step.output = "Multi-agent node loop executed successfully."

    # Parse structural state dictionaries
    decision = final_output.get("decision", {})
    action = decision.get("action", "UNKNOWN")
    reason = decision.get("reason", "No structural feedback returned.")
    fraud_score = final_output.get("fraud", {}).get("score", 0.0)
    audit = final_output.get("audit_result", {})

    # Design output visualization
    status_emoji = "🟢" if action == "APPROVE" else "🟡" if action == "REVIEW" else "🔴"
    if action == "BLOCKED":
        status_emoji = "🛡️ [GUARDRAIL BLOCK]"

    response_markdown = f"""
### {status_emoji} Adjudication Outcome for Claim `{claim_id}`

---

| Metric Node | Output Value |
| :--- | :--- |
| **Pipeline Decision** | `{action}` |
| **Computed Fraud Score** | `{fraud_score}` |
| **Database Audit Status** | `{"✅ Appended" if audit.get("audit_logged") else "❌ Skipped/Failed"}` |

> **Reasoning Summary:**
> {reason}
"""
    
    if audit.get("audit_logged"):
        response_markdown += f"\n\n<details><summary><b>View Database Transaction Logs</b></summary>\n\n```json\n{audit}\n```\n</details>"

    await cl.Message(content=response_markdown).send()
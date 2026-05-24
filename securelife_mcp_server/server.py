import os
import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="SecureLife MCP Server (Streamable HTTP)")

import os

# This looks in the root folder, the server folder, and your active terminal folder
possible_paths = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "SecureLife_claims.db")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "SecureLife_claims.db")),
    os.path.abspath("SecureLife_claims.db")
]

DB_PATH = None
for path in possible_paths:
    if os.path.exists(path):
        DB_PATH = path
        break

# Fallback path if it's missing everywhere
if not DB_PATH:
    DB_PATH = possible_paths

def get_db_connection():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"⚠ Database file not found at {DB_PATH}. Ensure SecureLife_claims.db is in the directory.")
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def query_claims(sql, params=()):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

# --- Request Data Models ---
class ClaimRequest(BaseModel):
    claim_id: str

class UpdateStatusRequest(BaseModel):
    claim_id: str
    new_status: str
    reason: str
    actor: str = "agent:claims_pipeline"

# --- Endpoints Mapping MCP Tools ---
@app.get("/tools/get_customer_names")
def get_customer_names():
    """Helper endpoint to feed customer lists safely to client-side Guardrails."""
    rows = query_claims("SELECT full_name FROM customers")
    return [r['full_name'] for r in rows]

@app.post("/tools/fetch_claim")
def fetch_claim_endpoint(req: ClaimRequest):
    """Fetch claim with joined customer + policy + hospital attributes."""
    rows = query_claims(
        """SELECT c.*, cu.full_name, cu.city,
                  p.policy_type, p.sum_insured, p.product_name,
                  h.name AS hospital_name, h.network_status, h.fraud_flag_count
           FROM claims c JOIN customers cu ON c.customer_id=cu.customer_id
           JOIN policies p ON c.policy_id=p.policy_id
           LEFT JOIN hospitals h ON c.hospital_id=h.hospital_id
           WHERE c.claim_id = ?""", (req.claim_id,))
    return rows if rows else {}

@app.post("/tools/verify_documents")
def verify_documents_endpoint(req: ClaimRequest):
    """Cross-check submitted vs required documents parameters."""
    rows = query_claims(
        """SELECT rd.doc_code, COALESCE(cd.status, 'MISSING') AS status
           FROM claims c
           JOIN required_documents rd ON c.policy_id IN
                (SELECT policy_id FROM policies WHERE policy_type = rd.claim_type)
           LEFT JOIN claim_documents cd ON cd.claim_id = c.claim_id AND cd.doc_code = rd.doc_code
           WHERE c.claim_id = ?""", (req.claim_id,))
    missing = [r['doc_code'] for r in rows if r['status'] == 'MISSING']
    return {
        "complete": len(missing) == 0, 
        "missing": missing,
        "submitted": [r['doc_code'] for r in rows if r['status'] == 'RECEIVED']
    }

@app.post("/tools/calculate_fraud_score")
def calculate_fraud_score_endpoint(req: ClaimRequest):
    """Sum the weights of all active fraud indicators for a claim transaction."""
    rows = query_claims(
        "SELECT indicator_code, description, weight FROM fraud_indicators WHERE claim_id = ?",
        (req.claim_id,))
    return {
        "score": round(sum(r['weight'] for r in rows), 2),
        "indicators": rows, 
        "count": len(rows)
    }

@app.post("/tools/update_claim_status")
def update_claim_status_endpoint(req: UpdateStatusRequest):
    """Atomically commit claim status changes and append rows to historical audit tables."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT status FROM claims WHERE claim_id = ?", (req.claim_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Claim {req.claim_id} not found")
        prev = row["status"]
        
        cur.execute("BEGIN TRANSACTION")
        cur.execute("UPDATE claims SET status = ? WHERE claim_id = ?", (req.new_status, req.claim_id))
        cur.execute(
            """INSERT INTO claim_history (claim_id, prev_status, new_status, actor, reason) 
               VALUES (?, ?, ?, ?, ?)""",
            (req.claim_id, prev, req.new_status, req.actor, req.reason))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
        
    return {
        "claim_id": req.claim_id, 
        "prev_status": prev, 
        "new_status": req.new_status,
        "actor": req.actor, 
        "audit_logged": True
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765)
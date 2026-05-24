import requests

class SecureLifeMCP:
    """Network-level client wrapper implementing streamable_http abstraction."""
    def __init__(self, base_url: str = "http://127.0.0.1:8765"):
        self.base_url = base_url

    def fetch_claim(self, claim_id: str) -> dict:
        resp = requests.post(f"{self.base_url}/tools/fetch_claim", json={"claim_id": claim_id})
        resp.raise_for_status()
        return resp.json()

    def verify_documents(self, claim_id: str) -> dict:
        resp = requests.post(f"{self.base_url}/tools/verify_documents", json={"claim_id": claim_id})
        resp.raise_for_status()
        return resp.json()

    def calculate_fraud_score(self, claim_id: str) -> dict:
        resp = requests.post(f"{self.base_url}/tools/calculate_fraud_score", json={"claim_id": claim_id})
        resp.raise_for_status()
        return resp.json()

    def update_claim_status(self, claim_id: str, new_status: str, reason: str, actor: str = "agent:claims_pipeline") -> dict:
        payload = {
            "claim_id": claim_id,
            "new_status": new_status,
            "reason": reason,
            "actor": actor
        }
        resp = requests.post(f"{self.base_url}/tools/update_claim_status", json=payload)
        resp.raise_for_status()
        return resp.json()
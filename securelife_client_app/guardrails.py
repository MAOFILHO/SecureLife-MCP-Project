import re
import requests
from typing import List, Tuple

_INJ = [
    r"ignore\s+(all\s+)?(previous|above)\s+instructions", r"system\s+prompt",
    r"jailbreak|DAN\s+mode", r"approve\s+(this|the|all)?\s*claims?\s+(regardless|anyway)",
    r"(set|reset)\s+fraud[_\s-]?score\s+to\s+0", r"bypass\s+(fraud|document|kyc)\s+check",
    r"\bUNION\s+SELECT\b", r"\bDROP\s+TABLE\b", r";\s*(SELECT|DROP|DELETE|UPDATE)", r"--\s*$"
]

_PII = {
    "PAN": r"[A-Z]{5}\d{4}[A-Z]", 
    "AADHAAR": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
    "IFSC": r"[A-Z]{4}0[A-Z0-9]{6}", 
    "PHONE": r"\+91[-\s]?[6-9]\d{9}",
    "EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
}

class GuardrailPipeline:
    def __init__(self, base_url: str = "http://127.0.0.1:8765"):
        try:
            # Dynamically seed known entity lists from the decoupled server backend
            resp = requests.get(f"{base_url}/tools/get_customer_names")
            resp.raise_for_status()
            self.known_names = resp.json()
        except Exception:
            self.known_names = []

    def check_input(self, text: str) -> Tuple[bool, List[str]]:
        if len(text) > 1500: 
            return False, ["oversize"]
        for pat in _INJ:
            if re.search(pat, text, re.IGNORECASE): 
                return False, [pat[:25]]
        return True, []

    def check_output(self, text: str) -> str:
        out = text
        for ptype, pat in _PII.items():
            out = re.sub(pat, f"[{ptype}_REDACTED]", out)
        for n in sorted(self.known_names, key=len, reverse=True):
            out = out.replace(n, "[NAME_REDACTED]")
        return out
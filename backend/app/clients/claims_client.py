# app/clients/claims_client.py (contract stub)
from typing import List, Dict, Any

def extract_claims_and_evidence(text:str) -> Dict[str, Any]:
    """
    Calls Daniel's service (e.g., http://localhost:8001/claims)
    Expected return:
    {
      "text_consistency": 0.64,
      "claims": [
        {
          "text": "...",
          "start_char": 420, "end_char": 462,
          "evidences": [
             {"type":"fact_check","source_name":"PolitiFact","source_url":"...","stance":"refutes","similarity":0.83,"snippet":"..."}
          ]
        }, ...
      ],
      "cross_reference": 0.30
    }
    """
    # For now, I implemented a mock and will replace with real HTTP call later
    return {
        "text_consistency": 0.6,
        "cross_reference": 0.3,
        "claims": []
    }

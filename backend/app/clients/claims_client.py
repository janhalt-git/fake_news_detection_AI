import json
import logging
from typing import List, Dict, Any
from ..config import settings
from .llm_client import LLMClient
from .politifact_client import CrossReferenceAdapter
from ..prompts import CLAIM_EXTRACTION_PROMPT, STANCE_DETECTION_PROMPT, SIMILARITY_SCORING_PROMPT


logger = logging.getLogger(__name__)

_llm_client = None
_cross_reference_adapter = None

def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient(
            provider=settings.llm_provider,
            model=settings.llm_model,
            api_key=settings.gemini_api_key
        )
    return _llm_client

def get_cross_reference_adapter() -> CrossReferenceAdapter:
    global _cross_reference_adapter
    if _cross_reference_adapter is None:
        _cross_reference_adapter = CrossReferenceAdapter()
    return _cross_reference_adapter

def extract_claims_and_evidence(text:str) -> Dict[str, Any]:
    """
    Main pipeline: extract claims and cross-reference against fact-checking sources.
    
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
    # Step 1: Extract claims
    claims = _extract_claims(text)

    # Step 2: For each claim, compute consistency metrics
    text_consistency_scores = []
    for claim in claims:
        score = _compute_text_consistency(claim["text"], text)
        text_consistency_scores.append(score)
    
    avg_text_consistency = sum(text_consistency_scores) / len(text_consistency_scores) if text_consistency_scores else 0.5

    # Step 3: Cross-reference claims against fact-checking sources
    adapter = get_cross_reference_adapter()
    all_similarities = []
    
    for claim in claims:
        evidence = adapter.cross_reference_claim(claim["text"], top_k=3)
        claim["evidences"] = evidence
        
        # Collect similarity scores for aggregate cross_reference metric
        for ev in evidence:
            all_similarities.append(ev["similarity"])
    
    cross_reference = sum(all_similarities) / len(all_similarities) if all_similarities else 0.0
    
    return {
        "text_consistency": avg_text_consistency,
        "cross_reference": cross_reference,
        "claims": claims
    }

def _extract_claims(text: str) -> List[Dict[str, Any]]:
    max_chars = 4000
    if len(text) > max_chars:
        text = text[:max_chars]
    
    prompt = CLAIM_EXTRACTION_PROMPT.format(text=text)
    
    result = get_llm_client().call(prompt, temperature=0.2, max_tokens=1000)
    response_text = result["response"].strip()
    
    logger.info(f"Claim extraction latency: {result['latency_ms']:.0f}ms")
    logger.debug(f"Claim extraction response: {response_text[:500]}")

    try:
        if "```" in response_text:
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        
        claims_data = json.loads(response_text)
        
        claims = []
        for item in claims_data:
            if isinstance(item, dict):
                # Handle both "fact" and "claim" keys
                claim_text = item.get("fact") or item.get("claim")
                if claim_text:
                    # Try to find character positions in original text
                    start_char = None
                    end_char = None
                    
                    # If LLM provided positions, use them; otherwise search for the claim in text
                    if item.get("start_char") is not None and item.get("end_char") is not None:
                        start_char = item.get("start_char")
                        end_char = item.get("end_char")
                    else:
                        # Search for claim text in original text (case-insensitive)
                        search_text = claim_text.lower()
                        text_lower = text.lower()
                        pos = text_lower.find(search_text)
                        if pos != -1:
                            start_char = pos
                            end_char = pos + len(claim_text)
                    
                    claims.append({
                        "text": claim_text,
                        "start_char": start_char,
                        "end_char": end_char,
                        "evidences": []
                    })
        
        logger.info(f"Extracted {len(claims)} claims")
        return claims
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse claim extraction response: {e}")
        logger.error(f"Response was: {response_text}")
        return []

def _compute_text_consistency(claim: str, text: str) -> float:
    prompt = STANCE_DETECTION_PROMPT.format(claim=claim, evidence=text[:2000])
    
    result = get_llm_client().call(prompt, temperature=0.1, max_tokens=100)
    response_text = result["response"].strip().lower()
    
    stance_scores = {
        "supports": 0.9,
        "support": 0.9,
        "refutes": 0.1,
        "refute": 0.1,
        "neutral": 0.5,
        "related_but_unclear": 0.4,
        "unclear": 0.4
    }
    
    # Try to find matching stance keyword
    for stance_keyword, score in stance_scores.items():
        if stance_keyword in response_text:
            return score
        
    # Default to neutral if no match found
    logger.warning(f"Could not determine stance from response: {response_text}")
    return 0.5
    
    '''# For now, I implemented a mock and will replace with real HTTP call later
    return {
        "text_consistency": 0.6,
        "cross_reference": 0.3,
        "claims": []
    }'''

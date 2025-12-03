import logging
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class PolitiFactClient:
    """
    Client to search and retrieve fact-checks from PolitiFact.
    
    PolitiFact provides a public API at:
    https://www.politifact.com/api/v/statements/
    """
    
    BASE_URL = "https://www.politifact.com/api/v/statements"
    
    def __init__(self, rate_limit_delay: float = 0.5):
        """
        Initialize PolitiFact client.
        
        Args:
            rate_limit_delay: Delay in seconds between API calls to respect rate limits
        """
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "FakeNewsDetectionAI/1.0"
        })
    
    def search(self, claim: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search PolitiFact for fact-checks matching a claim.
        
        Args:
            claim: The claim text to search for
            limit: Maximum number of results to return
            
        Returns:
            List of fact-check results with structure:
            [
                {
                    "statement": "The exact claim from PolitiFact",
                    "truth_meter": "true|mostly-true|half-true|mostly-false|false|pants-fire",
                    "truth_meter_score": 0.9,  # Converted to 0-1 scale
                    "article_url": "https://...",
                    "speaker": "Speaker name",
                    "source_url": "URL to fact-check",
                    "snippet": "Brief excerpt",
                    "publish_date": "YYYY-MM-DD"
                }
            ]
        """
        self._respect_rate_limit()
        
        try:
            # Search for statements matching the claim
            params = {
                "search": claim,
                "limit": limit
            }
            
            logger.info(f"Searching PolitiFact for: {claim}")
            response = self.session.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            # Parse the results
            for statement in data.get("results", []):
                result = self._parse_statement(statement)
                if result:
                    results.append(result)
            
            logger.info(f"Found {len(results)} PolitiFact results for claim")
            return results
            
        except requests.RequestException as e:
            logger.error(f"PolitiFact API error: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error parsing PolitiFact response: {str(e)}")
            return []
    
    def _parse_statement(self, statement: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a single statement from PolitiFact API response."""
        try:
            # Map PolitiFact truth ratings to scores
            truth_meter_map = {
                "true": 0.95,
                "mostly-true": 0.75,
                "half-true": 0.5,
                "mostly-false": 0.25,
                "false": 0.05,
                "pants-fire": 0.0,
                "unobservable": 0.5
            }
            
            rating = statement.get("rating", {})
            truth_meter = rating.get("slug", "unobservable").lower()
            
            return {
                "statement": statement.get("statement", ""),
                "truth_meter": truth_meter,
                "truth_meter_score": truth_meter_map.get(truth_meter, 0.5),
                "article_url": statement.get("article_url", ""),
                "speaker": self._get_speaker_name(statement),
                "source_url": f"https://www.politifact.com{statement.get('url', '')}",
                "snippet": self._get_snippet(statement),
                "publish_date": statement.get("date", "")[:10]  # Extract YYYY-MM-DD
            }
        except Exception as e:
            logger.warning(f"Failed to parse PolitiFact statement: {str(e)}")
            return None
    
    def _get_speaker_name(self, statement: Dict[str, Any]) -> str:
        """Extract speaker name from statement."""
        speaker = statement.get("speaker", {})
        if isinstance(speaker, dict):
            return speaker.get("name", "Unknown")
        return str(speaker) if speaker else "Unknown"
    
    def _get_snippet(self, statement: Dict[str, Any]) -> str:
        """Extract snippet from statement or article."""
        snippet = statement.get("statement", "")
        # Truncate to reasonable length
        if len(snippet) > 200:
            snippet = snippet[:197] + "..."
        return snippet
    
    def _respect_rate_limit(self):
        """Enforce rate limiting to avoid overwhelming the API."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()


class CrossReferenceAdapter:
    """
    Adapter to cross-reference claims against multiple fact-checking sources.
    Currently supports PolitiFact; can be extended for Snopes, FactCheck.org, etc.
    """
    
    def __init__(self):
        self.politifact = PolitiFactClient()
    
    def cross_reference_claim(self, claim: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Cross-reference a claim against multiple sources.
        
        Args:
            claim: The claim to fact-check
            top_k: Number of results per source to return
            
        Returns:
            List of evidence items with similarity and stance
        """
        all_evidence = []
        
        # Search PolitiFact
        politifact_results = self.politifact.search(claim, limit=top_k)
        for result in politifact_results:
            evidence = self._convert_to_evidence_format(
                result,
                source_name="PolitiFact",
                claim=claim
            )
            all_evidence.append(evidence)
        
        # Sort by similarity score (descending)
        all_evidence.sort(key=lambda x: x["similarity"], reverse=True)
        
        logger.info(f"Cross-referenced claim against {len(all_evidence)} sources")
        return all_evidence[:top_k]
    
    def _convert_to_evidence_format(
        self,
        result: Dict[str, Any],
        source_name: str,
        claim: str
    ) -> Dict[str, Any]:
        """
        Convert a fact-check result to the standard evidence format.
        
        Returns evidence dict with:
        {
            "type": "fact_check",
            "source_name": "PolitiFact",
            "source_url": "...",
            "stance": "supports|refutes|mixed|unrelated",
            "similarity": 0.85,
            "snippet": "..."
        }
        """
        # Map truth meter to stance
        truth_score = result.get("truth_meter_score", 0.5)
        
        if truth_score >= 0.7:
            stance = "supports"
        elif truth_score <= 0.3:
            stance = "refutes"
        else:
            stance = "mixed"
        
        # Simple semantic similarity: use keyword overlap ratio
        similarity = self._compute_similarity(claim, result.get("statement", ""))
        
        return {
            "type": "fact_check",
            "source_name": source_name,
            "source_url": result.get("source_url", ""),
            "stance": stance,
            "similarity": similarity,
            "snippet": result.get("snippet", ""),
            "truth_meter": result.get("truth_meter", ""),
            "truth_meter_score": result.get("truth_meter_score", 0.5)
        }
    
    def _compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute simple semantic similarity using word overlap.
        Returns a score between 0 and 1.
        
        For production, consider using:
        - Sentence transformers
        - Cosine similarity with embeddings
        - Fuzzy string matching
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        # Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        similarity = intersection / union if union > 0 else 0.0
        return min(similarity * 1.5, 1.0)  # Scale up slightly, cap at 1.0

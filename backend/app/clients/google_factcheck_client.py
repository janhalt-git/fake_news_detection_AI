import logging
import requests
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import time
import os

logger = logging.getLogger(__name__)


class ResultCache:
    """
    File-based cache for fact-check results with TTL support.
    """
    
    def __init__(self, cache_dir: str = "./cache/fact_checks", ttl_hours: int = 168):
        """
        Initialize cache.
        
        Args:
            cache_dir: Directory to store cache files
            ttl_hours: Time-to-live in hours (default: 7 days)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)
    
    def _get_cache_key(self, claim: str) -> str:
        """Generate cache key from claim text."""
        return hashlib.md5(claim.lower().encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get file path for cache key."""
        return self.cache_dir / f"{cache_key}.json"
    
    def get(self, claim: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve cached results for a claim.
        
        Args:
            claim: The claim text
            
        Returns:
            Cached results or None if not found/expired
        """
        cache_key = self._get_cache_key(claim)
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            
            # Check if expired
            cached_time = datetime.fromisoformat(cached_data["timestamp"])
            if datetime.now() - cached_time > self.ttl:
                logger.info(f"Cache expired for claim: {claim[:50]}...")
                cache_path.unlink()
                return None
            
            logger.info(f"Cache hit for claim: {claim[:50]}...")
            return cached_data["results"]
            
        except Exception as e:
            logger.warning(f"Failed to read cache: {str(e)}")
            return None
    
    def set(self, claim: str, results: List[Dict[str, Any]]):
        """
        Store results in cache.
        
        Args:
            claim: The claim text
            results: List of fact-check results
        """
        cache_key = self._get_cache_key(claim)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            cached_data = {
                "timestamp": datetime.now().isoformat(),
                "claim": claim,
                "results": results
            }
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cached_data, f, indent=2)
            
            logger.info(f"Cached {len(results)} results for claim: {claim[:50]}...")
            
        except Exception as e:
            logger.warning(f"Failed to write cache: {str(e)}")


class GoogleFactCheckClient:
    """
    Client for Google Fact Check Tools API.
    Aggregates fact-checks from multiple sources including PolitiFact, Snopes, FactCheck.org, etc.
    """
    
    BASE_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
    
    def __init__(self, api_key: str, rate_limit_delay: float = 1.0, use_cache: bool = True):
        """
        Initialize Google Fact Check client.
        
        Args:
            api_key: Google Cloud API key with Fact Check Tools API enabled
            rate_limit_delay: Delay in seconds between API calls
            use_cache: Whether to use file-based caching
        """
        self.api_key = api_key
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "FakeNewsDetectionAI/1.0"
        })
        self.cache = ResultCache() if use_cache else None
    
    def search(
        self,
        claim: str,
        limit: int = 10,
        language: str = "en",
        publisher_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for fact-checks matching a claim.
        
        Args:
            claim: The claim text to search for
            limit: Maximum number of results to return
            language: Language code (default: "en")
            publisher_filter: Filter by publisher domain (e.g., "snopes.com", "politifact.com")
            
        Returns:
            List of fact-check results with structure:
            [
                {
                    "statement": "The fact-checked claim",
                    "truth_rating": "true|mostly-true|mixture|mostly-false|false",
                    "truth_score": 0.85,  # 0-1 scale
                    "publisher": "PolitiFact",
                    "publisher_site": "politifact.com",
                    "source_url": "https://...",
                    "snippet": "Brief excerpt",
                    "publish_date": "2024-01-15",
                    "claimant": "Speaker name (if available)"
                }
            ]
        """
        # Check cache first
        if self.cache:
            cache_key = f"{claim}|{publisher_filter or 'all'}"
            cached_results = self.cache.get(cache_key)
            if cached_results is not None:
                return cached_results[:limit]
        
        self._respect_rate_limit()
        
        try:
            params = {
                "query": claim,
                "pageSize": min(limit, 100),  # API max is 100
                "languageCode": language,
                "key": self.api_key
            }
            
            if publisher_filter:
                params["reviewPublisherSiteFilter"] = publisher_filter
            
            logger.info(f"Searching Google Fact Check API for: {claim[:50]}...")
            response = self.session.get(self.BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            # Parse the results
            for claim_data in data.get("claims", []):
                result = self._parse_claim(claim_data)
                if result:
                    results.append(result)
            
            logger.info(f"Found {len(results)} fact-check results")
            
            # Cache the results
            if self.cache:
                self.cache.set(cache_key, results)
            
            return results[:limit]
            
        except requests.RequestException as e:
            logger.error(f"Google Fact Check API error: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text[:500]}")
            return []
        except Exception as e:
            logger.error(f"Error parsing Google Fact Check response: {str(e)}")
            return []
    
    def _parse_claim(self, claim_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a single claim from Google Fact Check API response."""
        try:
            reviews = claim_data.get("claimReview", [])
            if not reviews:
                return None
            
            # Use the first review (typically the most relevant)
            review = reviews[0]
            publisher = review.get("publisher", {})
            
            # Extract textual rating
            rating_text = review.get("textualRating", "").lower()
            truth_score = self._rating_to_score(rating_text)
            
            return {
                "statement": claim_data.get("text", ""),
                "truth_rating": rating_text,
                "truth_score": truth_score,
                "publisher": publisher.get("name", "Unknown"),
                "publisher_site": publisher.get("site", ""),
                "source_url": review.get("url", ""),
                "snippet": claim_data.get("text", "")[:300],
                "publish_date": review.get("reviewDate", "")[:10],
                "claimant": claim_data.get("claimant", {}).get("name", "")
            }
            
        except Exception as e:
            logger.warning(f"Failed to parse claim: {str(e)}")
            return None
    
    def _rating_to_score(self, rating: str) -> float:
        """
        Convert textual rating to numeric score (0-1).
        Handles various rating formats from different fact-checkers.
        """
        rating = rating.lower().strip()
        
        # Map common ratings to scores
        rating_map = {
            # True ratings
            "true": 0.95,
            "correct": 0.95,
            "accurate": 0.95,
            "mostly true": 0.75,
            "mostly correct": 0.75,
            
            # Mixed ratings
            "half true": 0.5,
            "mixture": 0.5,
            "mixed": 0.5,
            "unproven": 0.4,
            "undetermined": 0.4,
            
            # False ratings
            "mostly false": 0.25,
            "mostly incorrect": 0.25,
            "false": 0.05,
            "incorrect": 0.05,
            "pants on fire": 0.0,
            "pants-fire": 0.0,
            
            # Special cases
            "legend": 0.05,  # Snopes legend = false
            "outdated": 0.3,
            "misleading": 0.2
        }
        
        # Try exact match first
        if rating in rating_map:
            return rating_map[rating]
        
        # Try partial matches
        for key, value in rating_map.items():
            if key in rating:
                return value
        
        # Default to uncertain
        return 0.5
    
    def _respect_rate_limit(self):
        """Enforce rate limiting to avoid overwhelming the API."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()


class CrossReferenceAdapter:
    """
    High-level adapter for cross-referencing claims against Google Fact Check Tools API.
    Handles semantic similarity matching and result ranking.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize cross-reference adapter.
        
        Args:
            api_key: Google Cloud API key (defaults to GOOGLE_FACTCHECK_API_KEY env var)
        """
        if api_key is None:
            api_key = os.getenv("GOOGLE_FACTCHECK_API_KEY")
        
        if not api_key:
            logger.warning("No Google Fact Check API key provided. Cross-referencing disabled.")
            self.client = None
        else:
            self.client = GoogleFactCheckClient(api_key=api_key)
    
    def cross_reference_claim(self, claim: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Cross-reference a claim against multiple fact-checking sources.
        
        Args:
            claim: The claim to fact-check
            top_k: Number of results to return
            
        Returns:
            List of evidence items sorted by similarity:
            [
                {
                    "type": "fact_check",
                    "source_name": "PolitiFact",
                    "source_url": "https://...",
                    "stance": "supports|refutes|mixed",
                    "similarity": 0.85,
                    "snippet": "...",
                    "truth_meter": "mostly-true",
                    "truth_meter_score": 0.75
                }
            ]
        """
        if self.client is None:
            logger.warning("Cross-referencing disabled: no API key")
            return []
        
        # Search Google Fact Check API
        results = self.client.search(claim, limit=20)
        
        if not results:
            logger.info(f"No fact-checks found for claim: {claim[:50]}...")
            return []
        
        # Convert to evidence format and compute similarity
        evidence_list = []
        for result in results:
            similarity = self._compute_similarity(claim, result["statement"])
            
            # Only include results with reasonable similarity
            if similarity < 0.15:
                continue
            
            evidence = {
                "type": "fact_check",
                "source_name": result["publisher"],
                "source_url": result["source_url"],
                "stance": self._score_to_stance(result["truth_score"]),
                "similarity": similarity,
                "snippet": result["snippet"],
                "truth_meter": result["truth_rating"],
                "truth_meter_score": result["truth_score"]
            }
            evidence_list.append(evidence)
        
        # Sort by similarity (descending)
        evidence_list.sort(key=lambda x: x["similarity"], reverse=True)
        
        logger.info(f"Cross-referenced claim: found {len(evidence_list)} relevant fact-checks")
        return evidence_list[:top_k]
    
    def _compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute semantic similarity using multiple methods.
        
        Combines:
        - Jaccard similarity (word overlap)
        - Character-level fuzzy matching
        - Substring matching
        
        Returns score between 0 and 1.
        """
        if not text1 or not text2:
            return 0.0
        
        # Normalize texts
        t1 = text1.lower().strip()
        t2 = text2.lower().strip()
        
        # Method 1: Jaccard similarity (word-level)
        words1 = set(t1.split())
        words2 = set(t2.split())
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        jaccard = intersection / union if union > 0 else 0.0
        
        # Method 2: Character-level fuzzy matching
        fuzzy_score = self._fuzzy_ratio(t1, t2)
        
        # Method 3: Substring bonus
        substring_bonus = 0.0
        shorter = min(t1, t2, key=len)
        longer = max(t1, t2, key=len)
        if len(shorter) > 20 and shorter in longer:
            substring_bonus = 0.2
        
        # Weighted combination
        similarity = (0.6 * jaccard) + (0.3 * fuzzy_score) + substring_bonus
        
        return min(similarity, 1.0)
    
    def _fuzzy_ratio(self, s1: str, s2: str) -> float:
        """
        Simple character-level fuzzy matching.
        For production, consider using python-Levenshtein or rapidfuzz.
        """
        # Character bigram similarity
        def bigrams(s):
            return set(s[i:i+2] for i in range(len(s)-1))
        
        bg1 = bigrams(s1)
        bg2 = bigrams(s2)
        
        if not bg1 or not bg2:
            return 0.0
        
        intersection = len(bg1 & bg2)
        union = len(bg1 | bg2)
        
        return intersection / union if union > 0 else 0.0
    
    def _score_to_stance(self, truth_score: float) -> str:
        """
        Convert truth score to stance.
        
        Args:
            truth_score: Score from 0 (false) to 1 (true)
            
        Returns:
            "supports", "refutes", or "mixed"
        """
        if truth_score >= 0.7:
            return "supports"
        elif truth_score <= 0.3:
            return "refutes"
        else:
            return "mixed"

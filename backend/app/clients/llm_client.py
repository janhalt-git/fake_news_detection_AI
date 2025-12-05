import os
import json
import logging
import time
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self, provider: str, model: str, api_key: str):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.call_log = []
        
        if provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(model)

    def call(self, prompt: str, temperature: float = 0.3, max_tokens: int = 1000) -> Dict[str, Any]:
        """Call LLM and log the interaction."""
        start = time.time()

        try:
            response = self.client.generate_content(
                prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                }
            )
            result = {
                "response": response.text,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }

            latency_ms = (time.time() - start) * 1000
            result["latency_ms"] = latency_ms

            self._log_call(prompt, result)

            return result
        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}")
            raise

    def _log_call(self, prompt: str, result: Dict[str, Any]):
        """Log LLM calls for debugging and cost analysis."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "provider": self.provider,
            "model": self.model,
            "prompt_length": len(prompt),
            "tokens": result["total_tokens"],
            "latency_ms": result["latency_ms"],
            "response_length": len(result["response"])
        }
        
        self.call_log.append(log_entry)
        
        # Write to file
        log_dir = Path("./logs")
        log_dir.mkdir(exist_ok=True)
        
        with open(log_dir / "llm_calls.jsonl", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        logger.info(f"LLM Call: {log_entry}")
import logging
import json
import time
from typing import Any, Dict, Optional, Union
from openai import OpenAI
from web_research_agent.config import API_KEY, BASE_URL, MODEL_NAME
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

logger = logging.getLogger(__name__)

class LLMError(Exception):
    """Custom exception for LLM related errors."""
    pass

class LLMRateLimitError(LLMError):
    """Exception raised when 429 occurs."""
    pass

class LLMClient:
    def __init__(self):
        self.client = OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL
        )
        self.model = MODEL_NAME

    def _estimate_tokens(self, text: str) -> int:
        # Very rough estimate: 1 token approx 4 chars
        return len(text) // 4

    def _parse_json_robustly(self, text: str) -> Dict[str, Any]:
        """Tries to find JSON block if raw parsing fails."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown block
            import re
            match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass

            # Very basic attempt to find something that looks like JSON
            match = re.search(r'(\{.*\})', text, re.DOTALL)
            if match:
                 try:
                    return json.loads(match.group(1))
                 except json.JSONDecodeError:
                    pass

            raise LLMError("Failed to parse LLM response as JSON.")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=8),
        retry=retry_if_exception_type((LLMRateLimitError, Exception)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def call(self, prompt: str, system_prompt: str = "Assistant", response_format: Optional[str] = None) -> str:
        """Generic call with retry and monitoring."""
        start_time = time.time()
        prompt_size = self._estimate_tokens(prompt + system_prompt)

        try:
            kwargs = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3
            }
            if response_format == "json":
                kwargs["response_format"] = {"type": "json_object"}

            response = self.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ""
            latency = time.time() - start_time
            response_size = self._estimate_tokens(content)

            logger.info(f"LLM Call - Model: {self.model}, Latency: {latency:.2f}s, Prompt: ~{prompt_size}t, Response: ~{response_size}t")
            return content

        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "rate limit" in err_msg.lower():
                logger.warning(f"Rate limit detected: {err_msg}")
                raise LLMRateLimitError(err_msg)
            elif "503" in err_msg or "overloaded" in err_msg.lower():
                 logger.warning(f"Server overloaded (503): {err_msg}")
                 raise LLMError(err_msg)

            logger.error(f"LLM Call failed: {err_msg}")
            raise e

    def get_json(self, prompt: str, system_prompt: str = "Return JSON only.") -> Dict[str, Any]:
        """Get JSON with fallback parsing."""
        content = self.call(prompt, system_prompt, response_format="json")
        try:
            return self._parse_json_robustly(content)
        except Exception as e:
             logger.warning(f"JSON parsing failed on first attempt, retrying without json_format: {e}")
             # Retry once more but maybe without explicit JSON format if that helps some models
             content = self.call(prompt, system_prompt)
             return self._parse_json_robustly(content)

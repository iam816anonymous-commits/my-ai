import logging
import json
import time
import re
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
        return len(text) // 4

    def _parse_json_robustly(self, text: str) -> Dict[str, Any]:
        """Tries to find JSON block if raw parsing fails."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown block
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass

            # Find first { and last }
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                 try:
                    return json.loads(text[start:end+1])
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

        try:
            kwargs = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2
            }
            if response_format == "json":
                kwargs["response_format"] = {"type": "json_object"}

            response = self.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ""
            latency = time.time() - start_time

            logger.info(
                f"LLM Call - Model: {self.model}, Latency: {latency:.2f}s, "
                f"Prompt: ~{self._estimate_tokens(prompt + system_prompt)}t, "
                f"Response: ~{self._estimate_tokens(content)}t"
            )
            return content

        except Exception as e:
            err_msg = str(e)
            # Detect 429, 503, etc.
            if any(x in err_msg for x in ["429", "rate limit", "503", "overloaded", "timeout"]):
                logger.warning(f"Retryable LLM error: {err_msg}")
                raise LLMRateLimitError(err_msg)

            logger.error(f"Non-retryable LLM error: {err_msg}")
            raise e

    def get_json(self, prompt: str, system_prompt: str = "Return JSON.") -> Dict[str, Any]:
        """Get JSON with robust parsing and retries."""
        try:
            content = self.call(prompt, system_prompt, response_format="json")
            return self._parse_json_robustly(content)
        except Exception as e:
             logger.warning(f"JSON attempt failed, retrying without json_format: {e}")
             content = self.call(prompt, system_prompt)
             return self._parse_json_robustly(content)

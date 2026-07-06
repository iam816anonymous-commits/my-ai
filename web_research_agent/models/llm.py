import logging
import json
import time
import re
from typing import Any, Dict, Optional, Union
from openai import OpenAI
from web_research_agent.config import API_KEY, BASE_URL, MODEL_NAME, MAX_RETRIES, HTTP_REFERER, X_TITLE
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

logger = logging.getLogger(__name__)

class LLMError(Exception): pass
class LLMRateLimitError(LLMError): pass

class LLMClient:
    def __init__(self):
        headers = {}
        if HTTP_REFERER: headers["HTTP-Referer"] = HTTP_REFERER
        if X_TITLE: headers["X-Title"] = X_TITLE

        self.client = OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL,
            default_headers=headers
        )
        self.model = MODEL_NAME
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_cost_usd = 0.0

    def _estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        # Generic pricing: $0.15 / 1M prompt, $0.60 / 1M completion (similar to GPT-4o-mini)
        return (prompt_tokens * 0.15 / 1_000_000) + (completion_tokens * 0.60 / 1_000_000)

    def _parse_json_robustly(self, text: str) -> Dict[str, Any]:
        try: return json.loads(text)
        except:
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
            if match:
                try: return json.loads(match.group(1))
                except: pass
            start, end = text.find('{'), text.rfind('}')
            if start != -1 and end != -1:
                 try: return json.loads(text[start:end+1])
                 except: pass
            raise LLMError("JSON parse failed")

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=2, min=2, max=8),
        retry=retry_if_exception_type((LLMRateLimitError, Exception)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def call(self, prompt: str, system_prompt: str = "Assistant", response_format: Optional[str] = None) -> str:
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
                 try: kwargs["response_format"] = {"type": "json_object"}
                 except: pass

            response = self.client.chat.completions.create(**kwargs)
            if not response or not hasattr(response, 'choices') or not response.choices:
                raise LLMError("LLM response structure invalid: missing choices.")

            if not response.choices[0].message or response.choices[0].message.content is None:
                # Handle cases where message might be empty but valid (e.g. tool calls only, not expected here)
                raise LLMError("LLM response content is null or empty.")

            content = response.choices[0].message.content.strip()
            if not content and response_format != "json":
                raise LLMError("LLM returned empty string content.")

            # Use actual usage if available, else estimate
            if hasattr(response, 'usage') and response.usage:
                p_tokens = response.usage.prompt_tokens
                r_tokens = response.usage.completion_tokens
            else:
                p_tokens = self._estimate_tokens(prompt + system_prompt)
                r_tokens = self._estimate_tokens(content)

            self.total_prompt_tokens += p_tokens
            self.total_completion_tokens += r_tokens
            cost = self._calculate_cost(p_tokens, r_tokens)
            self.total_cost_usd += cost

            latency = time.time() - start_time
            logger.info(f"LLM [{self.model}] {latency:.2f}s | P: {p_tokens}t | R: {r_tokens}t | Cost: ${cost:.6f} | Total: {self.total_prompt_tokens + self.total_completion_tokens}t")
            return content

        except Exception as e:
            if any(x in str(e) for x in ["429", "rate limit", "503", "overloaded", "timeout"]):
                raise LLMRateLimitError(str(e))
            raise e

    def get_json(self, prompt: str, system_prompt: str = "Return JSON.") -> Dict[str, Any]:
        content = self.call(prompt, system_prompt, response_format="json")
        try: return self._parse_json_robustly(content)
        except:
             content = self.call(prompt + " Output valid JSON.", system_prompt)
             return self._parse_json_robustly(content)

    def summarize(self, text: str) -> str:
        """Compatibility wrapper for summarizer and extractor."""
        return self.call(text)

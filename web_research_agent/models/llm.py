import logging
from openai import OpenAI
from web_research_agent.config import API_KEY, BASE_URL, MODEL_NAME
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        if not API_KEY:
             logger.error("API_KEY not found in environment variables.")
        self.client = OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL
        )
        self.model = MODEL_NAME

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def summarize(self, text: str) -> str:
        """
        Summarizes the given text using the LLM. Retries up to 3 times.
        """
        if not text:
            return "No content to summarize."

        prompt = f"""
        Summarize the following article text.
        Your summary must include:
        - Main topic
        - Important findings
        - Important numbers (if any)
        - Key insights
        - Limitations (if any)

        Format the output in Markdown.

        Article Text:
        {text[:12000]} # Basic truncation to avoid token limits
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful research assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("LLM returned empty summary.")
            return content
        except Exception as e:
            logger.error(f"LLM Summarization attempt failed: {str(e)}")
            raise e

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate_report(self, summaries: str, objectives: list, topic: str) -> str:
        """
        Generates a final report from multiple article summaries and research objectives.
        Retries up to 3 times.
        """
        objectives_str = "\n".join([f"- {obj}" for obj in objectives])
        prompt = f"""
        Generate a comprehensive research report for the topic "{topic}" based on the following article summaries.
        The research objectives were:
        {objectives_str}

        The report must follow this exact structure:
        # Research Report: {topic}

        ## Executive Summary
        (A high-level overview of the research findings)

        ## Research Objectives
        (List the objectives addressed in this research)

        ## Methodology
        (Describe the research process: planning, targeted searches, content extraction, and LLM-based synthesis)

        ## Source Summaries
        (Incorporate the provided summaries here, organized logically by subtopic)

        ## Final Conclusion
        (Synthesize all information into a final conclusion)

        ## Coverage Summary
        (Discuss how well the research objectives were met)

        ## Confidence Score
        (Provide a confidence score from 0.0 to 1.0)

        ## Known Gaps
        (Identify areas that require further research)

        Summaries:
        {summaries}

        Ensure the response is a well-formatted Markdown document.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional research report writer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("LLM returned empty report.")
            return content
        except Exception as e:
            logger.error(f"LLM Report generation attempt failed: {str(e)}")
            raise e

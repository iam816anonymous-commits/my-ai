import logging
from openai import OpenAI
from web_research_agent.config import API_KEY, BASE_URL, MODEL_NAME

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.client = OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL
        )
        self.model = MODEL_NAME

    def summarize(self, text: str) -> str:
        """
        Summarizes the given text using the LLM.
        """
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
        {text}
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
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM Summarization failed: {e}")
            return "Summarization failed."

    def generate_report(self, summaries: str) -> str:
        """
        Generates a final report from multiple article summaries.
        """
        prompt = f"""
        Generate a comprehensive research report based on the following article summaries.

        The report must follow this exact structure:
        # Research Report

        ## Executive Summary
        (A high-level overview of the research findings)

        ## Source Summaries
        (Incorporate the provided summaries here, organized logically)

        ## Final Conclusion
        (Synthesize all information into a final conclusion)

        Summaries:
        {summaries}
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful research assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM Report generation failed: {e}")
            return "Report generation failed."

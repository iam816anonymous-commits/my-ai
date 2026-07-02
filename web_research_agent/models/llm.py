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

    def generate_report(self, summaries: str, objectives: list, topic: str) -> str:
        """
        Generates a final report from multiple article summaries and research objectives.
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
        (Describe the research process: multiple web searches, content extraction, and LLM-based summarization and synthesis)

        ## Source Summaries
        (Incorporate the provided summaries here, organized logically by subtopic if possible)

        ## Final Conclusion
        (Synthesize all information into a final conclusion)

        ## Coverage Summary
        (Discuss how well the research objectives were met based on the available sources)

        ## Confidence Score
        (Provide a confidence score from 0.0 to 1.0 based on the quality and diversity of sources)

        ## Known Gaps
        (Identify areas that were not fully covered or require further research)

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
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM Report generation failed: {e}")
            return "Report generation failed."

from typing import List
from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import ArticleSummary, ResearchPlan

def generate_final_report(summaries: List[ArticleSummary], plan: ResearchPlan, llm_client: LLMClient) -> str:
    """
    Combines summaries into a final Markdown report using LLM for synthesis.
    """
    combined_summaries = ""
    references = "\n## References\n\n"

    for i, item in enumerate(summaries, 1):
        url = item.url
        summary = item.summary

        combined_summaries += f"### Source {i}\nSource: {url}\n\n{summary}\n\n---\n\n"
        references += f"- {url}\n"

    final_report_content = llm_client.generate_report(
        summaries=combined_summaries,
        objectives=plan.objectives,
        topic=plan.topic
    )

    # Ensure references are at the end if not already included by LLM
    if "## References" not in final_report_content:
        final_report_content += references

    return final_report_content

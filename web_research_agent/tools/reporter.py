from typing import List
from web_research_agent.models.llm import LLMClient

def generate_final_report(summaries: List[dict], llm_client: LLMClient) -> str:
    """
    Combines summaries into a final Markdown report.
    Expects summaries to be a list of dicts with 'url' and 'summary' keys.
    """
    combined_summaries = ""
    references = "\n## References\n\n"

    for i, item in enumerate(summaries, 1):
        url = item.get('url', 'Unknown URL')
        summary = item.get('summary', 'No summary available.')

        combined_summaries += f"### Source {i}\nSource: {url}\n\n{summary}\n\n---\n\n"
        references += f"- {url}\n"

    final_report_content = llm_client.generate_report(combined_summaries)

    # Ensure references are at the end if not already included by LLM
    if "## References" not in final_report_content:
        final_report_content += references

    return final_report_content

from web_research_agent.models.llm import LLMClient

def summarize_article(text: str, llm_client: LLMClient) -> str:
    """
    Summarizes an individual article.
    """
    if not text:
        return "No content to summarize."

    return llm_client.summarize(text)

import logging
import re
from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import ResearchPlan
import math

logger = logging.getLogger(__name__)

def score_sentence(sentence: str) -> float:
    """
    Scores a sentence based on its length and presence of informative keywords.
    """
    words = sentence.split()
    if len(words) < 5 or len(words) > 40:
        return 0.0

    score = 1.0
    # Prefer sentences with numbers or capital letters (potential names/entities)
    if any(char.isdigit() for char in sentence):
        score += 0.5
    if any(word[0].isupper() for word in words if word):
        score += 0.3

    return score

def generate_fallback_summary(text: str) -> str:
    """
    Sophisticated local extractive summarizer.
    """
    # Clean text first
    text = re.sub(r'\[\d+\]', '', text) # Remove wiki references

    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if not paragraphs:
        return "Fallback summary: No content found."

    # Sentence tokenization (simple)
    sentences = []
    for p in paragraphs:
        # Split by . ! ? followed by space or end of string
        sents = re.split(r'(?<=[.!?])\s+', p)
        sentences.extend([s.strip() for s in sents if s.strip()])

    if not sentences:
        return "Fallback summary: No sentences found."

    # Score sentences
    scored_sentences = []
    for i, sent in enumerate(sentences):
        score = score_sentence(sent)

        # Position boost (first sentences of paragraphs often more important)
        if i == 0:
            score += 1.0

        scored_sentences.append((sent, score))

    # Sort and pick top sentences
    scored_sentences.sort(key=lambda x: x[1], reverse=True)

    top_sentences = scored_sentences[:10] # Pick top 10 informative sentences
    # Re-order based on original appearance to maintain flow
    original_order = {sent: i for i, (sent, _) in enumerate(zip(sentences, range(len(sentences))))}
    top_sentences.sort(key=lambda x: sentences.index(x[0]))

    summary_text = ' '.join([s[0] for s in top_sentences])

    # Final length check (approx 150-250 words)
    words = summary_text.split()
    if len(words) > 250:
        summary_text = ' '.join(words[:250]) + "..."

    return f"**Fallback summary (LLM unavailable)**\n\n{summary_text}"

def summarize_article(text: str, llm_client: LLMClient) -> str:
    """
    Summarizes text using LLM, with a high-quality fallback.
    """
    sys_prompt = "You are a professional research analyst. Summarize this article in 150-250 words. Focus on core evidence and data. Output Markdown."
    truncated_text = text[:4000]
    prompt = f"Summarize the following research material for a professional report:\n\n{truncated_text}"

    try:
        return llm_client.call(prompt, sys_prompt)
    except Exception as e:
        logger.warning(f"Summarization failed: {e}. Using local extractive fallback.")
        return generate_fallback_summary(text)

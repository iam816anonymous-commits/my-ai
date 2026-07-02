# Web Research Agent

A reasoning-driven research agent that plans, researches, and synthesizes high-quality reports. Optimized for free OpenRouter models.

## Features

- **Reasoning Loop**: Iteratively researches until objectives are met (max 3 cycles).
- **Intelligent Planning**: Decomposes queries into multiple research objectives and search terms.
- **Analytical Synthesis**: Produces professional research reports instead of summary lists.
- **Robustness**: Advanced fallback mechanisms for summarization and reporting.
- **OpenRouter Optimized**: Tuned for free models with robust JSON parsing and token efficiency.

## Installation

1. Install dependencies:
```bash
pip install -r web_research_agent/requirements.txt
```

2. Setup environment:
```bash
cp web_research_agent/.env.example web_research_agent/.env
```

## Environment Variables

The agent is configured via the `.env` file in the `web_research_agent/` directory.

| Variable | Description | Default |
|----------|-------------|---------|
| `API_KEY` | Your LLM provider API key (e.g., OpenRouter). | Required |
| `BASE_URL` | API base URL. | `https://openrouter.ai/api/v1` |
| `MODEL_NAME` | The LLM model to use. | `nvidia/nemotron-3-ultra-550b-a55b:free` |
| `MAX_ITERATIONS` | Maximum number of research/reasoning cycles. | `3` |
| `MAX_SEARCH_RESULTS` | Number of high-quality URLs to process per cycle. | `5` |
| `MAX_ARTICLE_CHARS` | Character limit for extracted text per page. | `4000` |
| `MAX_RETRIES` | Number of retry attempts for LLM/API calls. | `3` |
| `REQUEST_TIMEOUT` | Timeout in seconds for network requests. | `30` |
| `LOG_LEVEL` | Logging verbosity (DEBUG, INFO, WARNING, ERROR). | `INFO` |
| `DEBUG` | Enable detailed debug logging (true/false). | `false` |
| `HTTP_REFERER` | (Optional) OpenRouter header for site attribution. | |
| `X_TITLE` | (Optional) OpenRouter header for application title. | `Web Research Agent` |

### Setup Commands

**Linux / macOS:**
```bash
export PYTHONPATH=$PYTHONPATH:.
cp web_research_agent/.env.example web_research_agent/.env
# Edit web_research_agent/.env with your API_KEY
python web_research_agent/main.py "Your research query"
```

**Windows (PowerShell):**
```powershell
$env:PYTHONPATH += ";."
copy web_research_agent/.env.example web_research_agent/.env
# Edit web_research_agent/.env with your API_KEY
python web_research_agent/main.py "Your research query"
```

## Project Architecture

- `agents/researcher.py`: Core reasoning loop orchestration.
- `tools/planner.py`: Initial research strategy and objective generation.
- `tools/reasoner.py`: Analyzes coverage and generates follow-up queries.
- `tools/search.py`: Multi-query web searching and domain-based ranking.
- `tools/extractor.py`: Aggressive HTML noise removal and deduplication.
- `tools/summarizer.py`: LLM-based summarization with extractive local fallback.
- `tools/reporter.py`: Final report synthesis and fallback generation.
- `models/llm.py`: Robust LLM client with retries and JSON fallback.

## Running the Project

```bash
export PYTHONPATH=$PYTHONPATH:.
python web_research_agent/main.py "Topic to research"
```

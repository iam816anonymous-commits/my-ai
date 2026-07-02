# Web Research Agent

A reliable pipeline that researches a topic and generates a well-structured Markdown report.

## Features

- Web search using DuckDuckGo
- Page content extraction using Trafilatura and BeautifulSoup
- Article summarization using LLMs (OpenAI-compatible)
- Comprehensive report generation

## Installation

1. Install the required dependencies:

```bash
pip install -r web_research_agent/requirements.txt
```

2. Create a `.env` file in `web_research_agent/` (or set environment variables):

```env
API_KEY=your_api_key
BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4o
```

## Running the Project

To run the research agent, use the following command from the project root:

```bash
export PYTHONPATH=$PYTHONPATH:.
python web_research_agent/main.py "Your research query here"
```

The final report will be saved in `web_research_agent/output/report.md`.

## Project Architecture

- `main.py`: Entry point for the CLI.
- `config.py`: Configuration and environment variable loading.
- `agents/researcher.py`: Orchestrates the search, download, extraction, and summarization workflow.
- `tools/search.py`: Handles web searching and URL filtering.
- `tools/browser.py`: Downloads webpage HTML.
- `tools/extractor.py`: Extracts main article text from HTML.
- `tools/summarizer.py`: Summarizes individual articles using LLMs.
- `tools/reporter.py`: Assembles the final Markdown report.
- `models/llm.py`: Abstract client for LLM interactions.

## Future Improvements

- Support for more search engines.
- Improved extraction for complex layouts.
- Concurrent processing of URLs for faster results.
- Custom report templates.

from pydantic import BaseModel, HttpUrl
from typing import List, Optional

class SearchResult(BaseModel):
    url: HttpUrl

class ArticleSummary(BaseModel):
    url: str
    summary: str

class ResearchReport(BaseModel):
    title: str
    executive_summary: str
    source_summaries: List[ArticleSummary]
    final_conclusion: str
    references: List[str]

import json
import time
import os
import psutil
import statistics
from datetime import datetime
from typing import List, Dict, Any
from web_research_agent.agents.researcher import ResearchAgent
from web_research_agent.config import OUTPUT_DIR
from web_research_agent.models.schemas import BenchmarkMetrics

class BenchmarkEngine:
    def __init__(self, questions_path: str = "web_research_agent/benchmark/questions.json"):
        with open(questions_path, "r") as f:
            self.data = json.load(f)
        self.results = []

    def run_benchmark(self, limit: int = None):
        questions = self.data["questions"]
        if limit: questions = questions[:limit]

        for i, item in enumerate(questions, 1):
            category, query = item["category"], item["query"]
            print(f"[{i}/{len(questions)}] {category}: {query}")

            start_time = time.time()
            process = psutil.Process(os.getpid())

            agent = ResearchAgent()
            try:
                state, evaluation = agent.run(query)
                duration = time.time() - start_time

                # Enhanced Metrics
                avg_cov = sum(state.objective_coverage.values()) / len(state.objective_coverage) if state.objective_coverage else 0

                metrics = BenchmarkMetrics(
                    query=query, category=category, runtime=round(duration, 2),
                    pages_searched=state.iterations * 5,
                    successful_downloads=state.successful_downloads,
                    extraction_success=state.successful_extractions,
                    summary_success=state.successful_summaries,
                    evidence_count=len(state.evidence_graph.items),
                    citation_count=len(state.summaries),
                    coverage=round(avg_cov, 2),
                    confidence=state.confidence_breakdown.overall if state.confidence_breakdown else 0,
                    overall_quality_score=evaluation.coverage_score,
                    grade=evaluation.overall_grade,
                    memory_peak_mb=round(process.memory_info().rss / (1024 * 1024), 2),
                    source_quality_avg=sum(s.quality_score for s in state.summaries)/len(state.summaries) if state.summaries else 0
                )
                self.results.append(metrics.model_dump())
            except Exception as e:
                print(f"Fail: {e}")

        self.save_results()

    def save_results(self):
        output = "web_research_agent/benchmark/latest_results.json"
        data = []
        for r in self.results:
             item = r.copy()
             if isinstance(item.get("timestamp"), datetime): item["timestamp"] = item["timestamp"].isoformat()
             data.append(item)
        with open(output, "w") as f: json.dump(data, f, indent=2)

if __name__ == "__main__":
    engine = BenchmarkEngine()
    engine.run_benchmark(limit=3)

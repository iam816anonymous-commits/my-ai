import json
import time
import os
import psutil
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
        self.baseline_path = "web_research_agent/benchmark/baseline.json"
        self.baseline = {}
        if os.path.exists(self.baseline_path):
            with open(self.baseline_path, "r") as f:
                self.baseline = json.load(f)

    def run_benchmark(self, limit: int = None):
        questions = self.data["questions"]
        if limit:
            questions = questions[:limit]

        print(f"Starting benchmark for {len(questions)} queries...")

        for i, item in enumerate(questions, 1):
            category = item["category"]
            query = item["query"]
            print(f"[{i}/{len(questions)}] Category: {category} | Query: {query}")

            start_time = time.time()
            process = psutil.Process(os.getpid())
            start_mem = process.memory_info().rss

            agent = ResearchAgent()
            try:
                state, evaluation = agent.run(query)

                end_time = time.time()
                end_mem = process.memory_info().rss

                duration = end_time - start_time
                peak_mem = end_mem # Simplified peak mem

                # Calculate avg coverage
                avg_coverage = sum(state.objective_coverage.values()) / len(state.objective_coverage) if state.objective_coverage else 0

                metrics = BenchmarkMetrics(
                    query=query,
                    category=category,
                    runtime=round(duration, 2),
                    pages_searched=state.iterations * 5, # Estimate
                    successful_downloads=state.successful_downloads,
                    extraction_success=state.successful_extractions,
                    summary_success=state.successful_summaries,
                    evidence_count=len(state.evidence_graph.items),
                    citation_count=len(state.summaries),
                    coverage=round(avg_coverage, 2),
                    confidence=state.confidence_score,
                    overall_quality_score=evaluation.coverage_score, # Proxy
                    grade=evaluation.overall_grade,
                    memory_peak_mb=round(peak_mem / (1024 * 1024), 2),
                    source_quality_avg=sum(s.quality_score for s in state.summaries)/len(state.summaries) if state.summaries else 0
                )

                self.results.append(metrics.model_dump())

            except Exception as e:
                print(f"Benchmark failed for {query}: {e}")
                self.results.append({
                    "query": query,
                    "category": category,
                    "status": "failed",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })

        self.save_results()

    def save_results(self):
        output_path = "web_research_agent/benchmark/latest_results.json"
        # Convert datetime objects to string
        data_to_save = []
        for r in self.results:
             item = r.copy()
             if isinstance(item.get("timestamp"), datetime):
                  item["timestamp"] = item["timestamp"].isoformat()
             data_to_save.append(item)

        with open(output_path, "w") as f:
            json.dump(data_to_save, f, indent=2)
        print(f"Benchmark results saved to {output_path}")

    def run_regression_test(self):
        if not self.baseline:
            print("No baseline found. Saving current results as baseline.")
            with open(self.baseline_path, "w") as f:
                json.dump(self.results, f, indent=2)
            return True

        latest_path = "web_research_agent/benchmark/latest_results.json"
        if not os.path.exists(latest_path):
             print("No latest results to compare.")
             return False

        with open(latest_path, "r") as f:
             latest = json.load(f)

        # Simple comparison logic
        regressions = []
        # Find matches by query
        baseline_map = {r["query"]: r for r in self.baseline}

        for l in latest:
             b = baseline_map.get(l["query"])
             if not b: continue

             if l.get("status") == "failed": continue

             if l["runtime"] > b["runtime"] * 1.5:
                  regressions.append(f"Runtime increased for {l['query']}: {b['runtime']}s -> {l['runtime']}s")
             if l["coverage"] < b["coverage"] * 0.9:
                  regressions.append(f"Coverage decreased for {l['query']}: {b['coverage']}% -> {l['coverage']}%")

        if regressions:
             print("REGRESSIONS DETECTED:")
             for r in regressions: print(f" - {r}")
             return False

        print("No significant regressions detected.")
        return True

if __name__ == "__main__":
    engine = BenchmarkEngine()
    engine.run_benchmark(limit=3)
    engine.run_regression_test()

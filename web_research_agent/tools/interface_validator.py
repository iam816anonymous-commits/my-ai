import importlib
import logging
import sys

logger = logging.getLogger(__name__)

def validate_module_interfaces():
    """
    Validates that all critical modules can be imported and expose expected public functions.
    This prevents 'Interface Drift' from breaking the production pipeline.
    """
    # Mapping of module paths to their required public members
    expected_interfaces = {
        "web_research_agent.agents.researcher": ["ResearchAgent"],
        "web_research_agent.tools.reasoner": ["evaluate_research", "update_knowledge_base", "calculate_production_confidence", "calculate_explainable_confidence"],
        "web_research_agent.tools.reporter": ["generate_final_report", "export_report", "run_self_evaluation", "validate_objective_completeness"],
        "web_research_agent.tools.search": ["search_web"],
        "web_research_agent.tools.browser": ["fetch_all"],
        "web_research_agent.tools.extractor": ["extract_all"],
        "web_research_agent.tools.summarizer": ["summarize_article"],
        "web_research_agent.tools.planner": ["generate_research_plan"],
        "web_research_agent.tools.storage": ["storage", "StorageManager"],
        "web_research_agent.models.llm": ["LLMClient"],
        "web_research_agent.models.schemas": ["ResearchState", "PipelineResult", "ObjectiveStatus"]
    }

    failures = []

    print("Validating Module Interfaces...")
    for module_path, members in expected_interfaces.items():
        try:
            module = importlib.import_module(module_path)
            for member in members:
                if not hasattr(module, member):
                    failures.append(f"Module '{module_path}' is missing expected member '{member}'")
        except ImportError as e:
            failures.append(f"Failed to import module '{module_path}': {e}")
        except Exception as e:
            failures.append(f"Error during validation of '{module_path}': {e}")

    if failures:
        print("\nCRITICAL: Module Interface Drift Detected!")
        for failure in failures:
            print(f" - {failure}")
        return False

    print("All Module Interfaces Validated Successfully.")
    return True

if __name__ == "__main__":
    # Ensure project root is in path
    import os
    sys.path.append(os.getcwd())
    if not validate_module_interfaces():
        sys.exit(1)
    sys.exit(0)

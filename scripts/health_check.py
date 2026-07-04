import sys
import requests
from rich import print as rprint
from web_research_agent.config import API_KEY, BASE_URL

def check_health():
    """Verifies API connectivity and provider health."""
    results = {"LLM": "Unknown", "Internet": "Unknown"}

    # 1. Connectivity
    try:
        requests.get("https://google.com", timeout=5)
        results["Internet"] = "Pass"
    except:
        results["Internet"] = "Fail"

    # 2. LLM Provider (Simple check if key is set and endpoint responds)
    if not API_KEY:
        results["LLM"] = "Fail (API_KEY missing)"
    else:
        try:
            # Simple models call to check health
            resp = requests.get(f"{BASE_URL}/models", headers={"Authorization": f"Bearer {API_KEY}"}, timeout=10)
            if resp.status_code == 200:
                results["LLM"] = "Pass"
            else:
                results["LLM"] = f"Fail (Status {resp.status_code})"
        except Exception as e:
            results["LLM"] = f"Fail ({str(e)})"

    rprint("\n[bold]Provider Health Status:[/bold]")
    for k, v in results.items():
        color = "green" if "Pass" in v else "red"
        rprint(f"- {k}: [{color}]{v}[/{color}]")

    return all("Pass" in str(v) for v in results.values())

if __name__ == "__main__":
    sys.exit(0 if check_health() else 1)

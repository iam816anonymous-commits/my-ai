# ROOT_CAUSE.md - Search Pipeline Regression Analysis

## 1. Regression Origin
The search pipeline regression originated from a lack of strict type validation for search queries. In Python, both `str` and `list` are iterable. When a `str` was accidentally passed to the search function (likely due to LLM response parsing or incorrect state updates), the loop over `queries` iterated character-by-character instead of processing the entire phrase.

For example, a query like `"search"` would be iterated as `'s'`, `'e'`, `'a'`, `'r'`, `'c'`, `'h'`, resulting in 6 separate, meaningless searches.

## 2. Why Strings Became Iterables
This behavior is a common pitfall in Python when using `for item in items:` without verifying that `items` is actually a collection of objects rather than a single string. The system was designed to handle `List[str]`, but lacked guards to prevent `str` from entering the search loop.

## 3. Files Modified
- **`web_research_agent/tools/search.py`**:
    - Replaced `duckduckgo_search` with the modern `ddgs` package.
    - Added strict validation in `search_web` to raise a `ValueError` if a `str` or non-`list` is received.
    - Added detailed debug printing for query inspection.
- **`web_research_agent/agents/researcher.py`**:
    - Added search validation to stop the pipeline if no unique URLs are discovered on the first iteration.
    - Ensured downstream stages (extraction, reasoning, synthesis) only execute if evidence exists.
- **`scripts/check_dependencies.py`**:
    - Updated dependency list to reflect the migration to `ddgs`.
- **`web_research_agent/requirements.txt`**:
    - Updated to `ddgs>=9.0.0`.

## 4. Regression Tests Added
A temporary regression test script was executed to verify the following:
1.  **Correct Type Handling**: Verified that `search_web` accepts `list[str]` and correctly identifies search results.
2.  **Strict Validation**: Confirmed that passing a `str` to `search_web` immediately raises a `ValueError` with a clear "CRITICAL REGRESSION" message.
3.  **Completeness**: Verified that queries like "What is Web3?" and "AI Coding Agents" produce valid, complete search phrases and discover evidence.

## 5. Prevention Safeguards
- **Pre-Retry Validation**: Validation is performed in the `search_web` wrapper *before* entering the retry-decorated `SearchEngineManager.search` method, ensuring fast failure and clear error messages.
- **Pipeline Integrity Guard**: The research agent now explicitly checks `new_urls` and halts execution if the initial search fails to provide a foundation for the report.

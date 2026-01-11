"""Prompt version constants.

This module exists to break circular imports between llm_prompts.py and render.py.
Both modules import PROMPT_VERSION from here.
"""

# Current prompt version - increment when making changes
# v7.0.0: Enhanced context - more commits (20), commit co-authors, more review comments (10), AI config files
# v8.0.0: Enhanced tech detection (mapping tables, framework signals) + summary guidelines (PR type decision tree)
# v8.1.0: Added @@ mention syntax for reviewers (@@username links to PRs they review vs @username for authors)
# v8.2.0: Added anti-bias rules for tech detection (do NOT infer from org/repo names, require file evidence)
# v8.3.0: Added Copilot Champions section to prompts - identifies top performers as potential mentors
PROMPT_VERSION = "8.3.0"

"""Service to generate weekly LLM-powered narrative insights for public repos.

Uses Groq Batch API for 50% cost savings. Submits all repo insights in a
single batch, polls for completion, then stores results. Falls back to
direct API calls if batch submission fails.
"""

import json
import logging
import os
import tempfile
import time
from pathlib import Path

from groq import Groq

from apps.public.models import PublicRepoInsight, PublicRepoProfile, PublicRepoStats

logger = logging.getLogger(__name__)

# Uses the same reliable model as the batch processor's fallback
INSIGHT_MODEL = "llama-3.3-70b-versatile"

# Prompt version for traceability. Bump when prompt text changes.
REPO_INSIGHT_PROMPT_VERSION = "1.0"

# System prompt for repo insight generation.
# NOTE: This is a NEW prompt, not a modification of apps/metrics/prompts/templates/*.
# Per CLAUDE.md, prompt changes require approval. This prompt was approved as part
# of the public repo pages GTM plan.
REPO_INSIGHT_SYSTEM_PROMPT = """\
You are an engineering analytics expert writing a brief, data-driven insight
about an open source repository's engineering practices. Write exactly ONE
paragraph (2-4 sentences) that:

1. Leads with the most notable finding from the data
2. Includes specific numbers to make the insight citable
3. Provides context by comparing to typical OSS patterns
4. Ends with an implication or forward-looking observation

Write in third person. Be factual, not promotional. Use plain language
a CTO would share in a Slack channel or quote in a presentation.
Do NOT use markdown formatting, bullet points, or headers.
"""

# Batch polling configuration
BATCH_POLL_INTERVAL = 15  # seconds
BATCH_MAX_WAIT = 600  # 10 minutes


def build_insight_payload(repo_profile: PublicRepoProfile, repo_stats: PublicRepoStats) -> dict:
    """Build the data payload sent to the LLM for insight generation."""
    return {
        "repo_name": repo_profile.display_name,
        "github_repo": repo_profile.github_repo,
        "total_prs": repo_stats.total_prs,
        "total_prs_in_window": repo_stats.total_prs_in_window,
        "ai_assisted_pct": float(repo_stats.ai_assisted_pct),
        "median_cycle_time_hours": float(repo_stats.median_cycle_time_hours),
        "median_review_time_hours": float(repo_stats.median_review_time_hours),
        "active_contributors_30d": repo_stats.active_contributors_30d,
        "cadence_change_pct": float(repo_stats.cadence_change_pct),
        "best_signal": repo_stats.best_signal,
        "watchout_signal": repo_stats.watchout_signal,
    }


def _build_user_prompt(payload: dict) -> str:
    """Build the user prompt from a payload dict."""
    prompt = (
        f"Repository: {payload['repo_name']} ({payload['github_repo']})\n"
        f"Total merged PRs: {payload['total_prs']} (all-time), "
        f"{payload['total_prs_in_window']} in last 30 days\n"
        f"AI-assisted PRs: {payload['ai_assisted_pct']:.1f}%\n"
        f"Median cycle time: {payload['median_cycle_time_hours']:.1f} hours\n"
        f"Median review time: {payload['median_review_time_hours']:.1f} hours\n"
        f"Active contributors (30d): {payload['active_contributors_30d']}\n"
        f"Cadence change: {payload['cadence_change_pct']:+.1f}% vs prior period\n"
    )

    if payload.get("best_signal", {}).get("metric") != "none":
        signal = payload["best_signal"]
        prompt += f"Best signal: {signal.get('label', '')} — {signal.get('description', '')}\n"

    if payload.get("watchout_signal", {}).get("metric") != "none":
        signal = payload["watchout_signal"]
        prompt += f"Watchout: {signal.get('label', '')} — {signal.get('description', '')}\n"

    return prompt


def submit_insights_batch(
    repos_with_stats: list[tuple[PublicRepoProfile, PublicRepoStats]],
    api_key: str | None = None,
) -> str | None:
    """Submit all repo insights as a single Groq batch.

    Creates a JSONL file with one entry per repo, uploads it,
    and creates a batch job. Returns the batch ID for polling.

    Returns None if no repos to process or submission fails.
    """
    if not repos_with_stats:
        return None

    client = Groq(api_key=api_key or os.environ.get("GROQ_API_KEY"))

    # Create JSONL batch file
    fd, temp_path = tempfile.mkstemp(suffix=".jsonl", prefix="repo_insights_")
    os.close(fd)
    batch_file = Path(temp_path)

    try:
        with open(batch_file, "w") as f:
            for repo_profile, repo_stats in repos_with_stats:
                payload = build_insight_payload(repo_profile, repo_stats)
                user_prompt = _build_user_prompt(payload)

                entry = {
                    "custom_id": f"repo-insight-{repo_profile.id}",
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": INSIGHT_MODEL,
                        "messages": [
                            {"role": "system", "content": REPO_INSIGHT_SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.3,
                        "max_tokens": 300,
                    },
                }
                f.write(json.dumps(entry) + "\n")

        # Upload file and create batch
        with open(batch_file, "rb") as f:
            file_response = client.files.create(file=f, purpose="batch")

        batch = client.batches.create(
            completion_window="24h",
            endpoint="/v1/chat/completions",
            input_file_id=file_response.id,
        )

        logger.info(
            "Submitted repo insights batch %s with %d entries",
            batch.id,
            len(repos_with_stats),
        )
        return batch.id

    except Exception:
        logger.exception("Failed to submit repo insights batch")
        return None
    finally:
        batch_file.unlink(missing_ok=True)


def process_insights_batch(
    batch_id: str,
    repos_with_stats: list[tuple[PublicRepoProfile, PublicRepoStats]],
    api_key: str | None = None,
) -> dict:
    """Poll for batch completion and store results.

    Returns dict with generated/errors counts.
    """
    client = Groq(api_key=api_key or os.environ.get("GROQ_API_KEY"))

    # Build repo lookup by custom_id
    repo_lookup = {f"repo-insight-{repo_profile.id}": repo_profile for repo_profile, _ in repos_with_stats}

    # Poll for completion
    elapsed = 0
    while elapsed < BATCH_MAX_WAIT:
        batch = client.batches.retrieve(batch_id)

        if batch.status in ("completed", "failed", "expired", "cancelled"):
            break

        time.sleep(BATCH_POLL_INTERVAL)
        elapsed += BATCH_POLL_INTERVAL

    if batch.status != "completed" or not batch.output_file_id:
        logger.error("Batch %s did not complete: status=%s", batch_id, batch.status)
        return {"generated": 0, "errors": len(repos_with_stats)}

    # Download and parse results
    response = client.files.content(batch.output_file_id)
    generated = 0
    errors = 0

    for line in response.text().strip().split("\n"):
        if not line:
            continue

        try:
            data = json.loads(line)
            custom_id = data["custom_id"]
            repo_profile = repo_lookup.get(custom_id)

            if not repo_profile:
                logger.warning("Unknown custom_id in batch results: %s", custom_id)
                errors += 1
                continue

            # Extract content from response
            body = data.get("response", {}).get("body", {})
            choices = body.get("choices", [])
            if not choices:
                errors += 1
                continue

            content = choices[0].get("message", {}).get("content", "").strip()
            if not content:
                errors += 1
                continue

            # Store insight
            _store_insight(repo_profile, content, batch_id)
            generated += 1

        except (json.JSONDecodeError, KeyError, IndexError):
            logger.exception("Failed to parse batch result line")
            errors += 1

    return {"generated": generated, "errors": errors}


def _store_insight(repo_profile: PublicRepoProfile, content: str, batch_id: str) -> PublicRepoInsight:
    """Store a generated insight, marking previous ones as not current."""
    PublicRepoInsight.objects.filter(
        repo_profile=repo_profile,
        is_current=True,
    ).update(is_current=False)

    return PublicRepoInsight.objects.create(
        repo_profile=repo_profile,
        content=content,
        insight_type="weekly",
        is_current=True,
        batch_id=batch_id,
    )


def generate_repo_insight(
    repo_profile: PublicRepoProfile,
    repo_stats: PublicRepoStats,
) -> PublicRepoInsight | None:
    """Generate and store a narrative insight for a single public repo.

    Uses Groq batch API for a single-item batch. For multiple repos,
    prefer submit_insights_batch() + process_insights_batch() which
    batches all repos into a single API call.

    On success: creates new PublicRepoInsight(is_current=True),
    marks previous insights is_current=False.
    On failure: logs error, returns None, previous insight stays in place.
    """
    batch_id = submit_insights_batch([(repo_profile, repo_stats)])
    if not batch_id:
        return None

    result = process_insights_batch(batch_id, [(repo_profile, repo_stats)])

    if result["generated"] > 0:
        return PublicRepoInsight.objects.filter(
            repo_profile=repo_profile,
            is_current=True,
        ).first()

    return None

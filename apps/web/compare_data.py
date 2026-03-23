"""Competitor comparison data for comparison pages.

This module contains all competitor data used by comparison views and templates.
Centralized here for easy updates when competitor pricing/features change.
"""

# Feature status constants
LIVE = "live"  # ✅ Available now
SOON = "coming_soon"  # 🔜 In development
PLANNED = "planned"  # 📋 On roadmap
NO = False  # ❌ Not available

# Our pricing (flat-rate tiers)
OUR_PRICING = {
    "trial": {"name": "Trial", "max_devs": None, "price_monthly": 0, "days": 30},
    "starter": {"name": "Starter", "max_devs": 10, "price_monthly": 99},
    "team": {"name": "Team", "max_devs": 50, "price_monthly": 299},
    "business": {"name": "Business", "max_devs": 150, "price_monthly": 699},
    "enterprise": {"name": "Enterprise", "max_devs": None, "price_monthly": None},
}

# Our features (honest status)
OUR_FEATURES = {
    "github": LIVE,
    "ai_code_detection": LIVE,
    "ai_usage_correlation": LIVE,
    "team_performance": LIVE,
    "insights": LIVE,
    "copilot_metrics": LIVE,
    "jira": SOON,
    "slack_surveys": SOON,
    "gamified_surveys": SOON,
    "dora_metrics": "partial",  # Cycle time yes, deployment freq no
    "developer_surveys": SOON,
    "soc2": PLANNED,
    "gitlab": NO,
    "bitbucket": NO,
}


def get_our_annual_cost(team_size: int) -> tuple[int, str]:
    """Calculate our annual cost for a team size.

    Returns:
        Tuple of (annual_cost, tier_name)
    """
    if team_size <= 10:
        return 99 * 12, "Starter"
    elif team_size <= 50:
        return 299 * 12, "Team"
    elif team_size <= 150:
        return 699 * 12, "Business"
    else:
        return None, "Enterprise"


def get_our_annual_cost_discounted(team_size: int) -> tuple[int | None, str]:
    """Calculate annual cost with 17% discount (2 months free).

    Annual billing gives customers 2 months free, which is ~17% off.
    This is a common SaaS pattern that encourages annual commitments.

    Returns:
        Tuple of (annual_cost, tier_name)
    """
    if team_size <= 10:
        return 99 * 10, "Starter"  # $990/year (2 months free)
    elif team_size <= 50:
        return 299 * 10, "Team"  # $2,990/year (2 months free)
    elif team_size <= 150:
        return 699 * 10, "Business"  # $6,990/year (2 months free)
    else:
        return None, "Enterprise"


# Competitor data
COMPETITORS = {
    "linearb": {
        "name": "LinearB",
        "slug": "linearb",
        "tagline": "Workflow automation + DORA metrics platform",
        "website": "https://linearb.io",
        "pricing_model": "per-seat",
        "pricing_range": "$35-46/seat/mo",
        "price_per_seat_low": 35,
        "price_per_seat_high": 46,
        "annual_cost_100_devs": 42000,
        "free_tier": "8 contributors",
        "priority": "high",
        "our_angle": "Delivery visibility for GitHub-first teams at flat-rate pricing",
        "one_liner": "Workflow automation + DORA. $35-46/seat.",
        "their_strengths": [
            "Active Dev Interrupted community (30K+ members)",
            "PR routing, approval rules, auto-merging",
            "Free tier for 8 contributors",
            "SOC 2 Type II certified",
            "Deep Jira integration",
        ],
        "our_advantages": [
            "70% cheaper ($299/mo vs $1,750+/mo for 50 devs)",
            "Flat-rate pricing (no per-seat anxiety)",
            "Clearer delivery visibility (not workflow automation)",
            "Faster setup, less complexity",
            "AI-related correlation without a separate module",
        ],
        "honest_gaps": [
            "They have Jira integration (ours coming soon)",
            "They have more workflow automation features",
            "They have SOC 2 (we're working on it)",
            "They support GitLab and Bitbucket",
        ],
        "best_for_them": "Teams prioritizing workflow automation and community",
        "best_for_us": (
            "Teams of 15-75 devs that want cycle time, review bottlenecks, "
            "and trend visibility without enterprise pricing"
        ),
        "features": {
            "ai_code_detection": "partial",
            "ai_usage_correlation": True,
            "gamified_surveys": False,
            "dora_metrics": True,
            "pr_insights": True,
            "github": True,
            "gitlab": True,
            "bitbucket": True,
            "jira": True,
            "slack": True,
            "soc2": True,
            "developer_surveys": False,
            "workflow_automation": True,
        },
        "seo": {
            "title": "Tformance vs LinearB: Pricing, Delivery Visibility & Honest Comparison",
            "description": (
                "LinearB alternative for GitHub-first teams that want delivery visibility, trend clarity, "
                "and flat-rate pricing without enterprise complexity."
            ),
            "keywords": [
                "linearb alternative",
                "linearb pricing",
                "linearb vs tformance",
                "linearb review",
            ],
        },
        "faqs": [
            {
                "question": "Is Tformance a good LinearB alternative?",
                "answer": (
                    "Yes, if delivery visibility matters more than workflow automation. "
                    "Tformance is a stronger fit for smaller teams that want "
                    "cycle time, review bottlenecks, and clear pricing."
                ),
            },
            {
                "question": "Does Tformance have all LinearB features?",
                "answer": (
                    "No. LinearB has Jira, workflow automation, full DORA. "
                    "We focus on delivery visibility and GitHub-first setup at a fraction of the cost."
                ),
            },
            {
                "question": "Can I migrate from LinearB to Tformance?",
                "answer": (
                    "Yes. Connect your GitHub repos via OAuth. "
                    "Historical data syncs automatically. No data export/import needed."
                ),
            },
            {
                "question": "Why is Tformance so much cheaper?",
                "answer": (
                    "Flat-rate pricing, not per-seat. Focused feature set. Early stage—this price won't last forever."
                ),
            },
            {
                "question": "Does LinearB offer a free trial?",
                "answer": (
                    "LinearB: 8 contributors free forever. Tformance: 30-day trial for any size, then flat-rate."
                ),
            },
        ],
    },
    "jellyfish": {
        "name": "Jellyfish",
        "slug": "jellyfish",
        "tagline": "Enterprise engineering intelligence platform",
        "website": "https://jellyfish.co",
        "pricing_model": "per-seat",
        "pricing_range": "~$50/seat/mo",
        "price_per_seat_low": 50,
        "price_per_seat_high": 50,
        "annual_cost_100_devs": 60000,
        "free_tier": None,
        "priority": "high",
        "our_angle": "Delivery visibility for growing teams without enterprise overhead",
        "one_liner": "Enterprise engineering intelligence. ~$50/seat.",
        "their_strengths": [
            "Enterprise-grade platform for 200+ dev teams",
            "R&D capitalization and DevFinOps features",
            "Deep Jira integration",
            "SOC 2 Type II certified",
            "Comprehensive executive reporting",
        ],
        "our_advantages": [
            "86% cheaper ($699/mo vs ~$5,000/mo for 100 devs)",
            "No enterprise sales process (start in 5 minutes)",
            "GitHub-first delivery visibility without enterprise sprawl",
            "Flat-rate pricing scales better",
        ],
        "honest_gaps": [
            "They have deep Jira integration",
            "They have R&D capitalization features",
            "They have DevFinOps and budget tracking",
            "They're proven at 1000+ engineer scale",
            "They have developer surveys built-in",
        ],
        "best_for_them": "Enterprise orgs (200+ devs) needing DevFinOps",
        "best_for_us": "Growing teams (15-75 devs) that want delivery visibility fast, no enterprise sales required",
        "features": {
            "ai_code_detection": False,
            "dora_metrics": True,
            "pr_insights": True,
            "github": True,
            "gitlab": True,
            "bitbucket": True,
            "jira": True,
            "slack": True,
            "soc2": True,
            "developer_surveys": True,
            "rd_capitalization": True,
            "devfinops": True,
        },
        "seo": {
            "title": "Tformance vs Jellyfish: Delivery Visibility Without Enterprise Pricing",
            "description": (
                "Jellyfish alternative for teams that want cycle time, review load, and repo trends "
                "without enterprise pricing or a long sales cycle."
            ),
            "keywords": [
                "jellyfish alternative",
                "jellyfish pricing",
                "jellyfish engineering",
                "jellyfish competitors",
            ],
        },
        "faqs": [
            {
                "question": "Is Tformance a good Jellyfish alternative?",
                "answer": (
                    "For teams under 150 devs focused on delivery visibility, yes. "
                    "For enterprise orgs needing R&D capitalization, Jellyfish is purpose-built."
                ),
            },
            {
                "question": "Why is Jellyfish so expensive?",
                "answer": (
                    "Enterprise features, sales, support. Worth it if you need all that. Overpaying if you don't."
                ),
            },
            {
                "question": "Can a 200+ dev team use Tformance?",
                "answer": (
                    "Yes, at our Enterprise tier (custom pricing). But honestly, "
                    "if you're 200+ devs with enterprise requirements, evaluate Jellyfish too."
                ),
            },
            {
                "question": "Does Tformance do R&D capitalization?",
                "answer": (
                    "No. That's not our focus. If CapEx/OpEx tracking is critical, "
                    "Jellyfish or similar enterprise tools are better fits."
                ),
            },
        ],
    },
    "swarmia": {
        "name": "Swarmia",
        "slug": "swarmia",
        "tagline": "Developer experience and productivity platform",
        "website": "https://swarmia.com",
        "pricing_model": "per-dev-modular",
        "pricing_range": "€22-42/dev/mo",
        "price_per_seat_low": 24,
        "price_per_seat_high": 46,
        "annual_cost_100_devs": 50400,
        "free_tier": None,
        "priority": "high",
        "our_angle": "Delivery visibility with flat pricing, not module math",
        "one_liner": "DevEx surveys + productivity. €22-42/dev.",
        "their_strengths": [
            "Built-in developer experience surveys",
            "Working agreements and team rituals",
            "Full DORA metrics suite",
            "Modular pricing (pick your features)",
            "Strong European presence",
        ],
        "our_advantages": [
            "Flat-rate pricing (no module math)",
            "AI-related correlation as a secondary lens",
            "Simpler setup, faster time-to-value",
            "Budget-friendly for larger teams",
        ],
        "honest_gaps": [
            "They have developer surveys (ours coming)",
            "They have working agreements features",
            "They have full DORA metrics",
            "They have Slack integration",
        ],
        "best_for_them": "Teams prioritizing developer experience surveys",
        "best_for_us": "Teams of 15-75 devs wanting delivery visibility plus flat pricing",
        "features": {
            "ai_code_detection": False,
            "dora_metrics": True,
            "pr_insights": True,
            "github": True,
            "gitlab": True,
            "jira": True,
            "slack": True,
            "soc2": True,
            "developer_surveys": True,
            "working_agreements": True,
        },
        "seo": {
            "title": "Tformance vs Swarmia: Delivery Visibility Comparison 2026",
            "description": (
                "Swarmia alternative for GitHub-first teams that want simpler pricing, delivery visibility, "
                "and a faster path to useful metrics."
            ),
            "keywords": [
                "swarmia alternative",
                "swarmia pricing",
                "swarmia review",
                "developer productivity platform",
            ],
        },
        "faqs": [
            {
                "question": "Is Tformance a good Swarmia alternative?",
                "answer": (
                    "If delivery visibility and simpler pricing are your priority, yes. "
                    "If developer experience surveys and team health are primary, "
                    "Swarmia is built for that."
                ),
            },
            {
                "question": "Does Swarmia detect AI tool usage?",
                "answer": (
                    "Not as a core surface. Swarmia tracks developer productivity broadly, "
                    "while Tformance uses AI-related signals as supporting context next to delivery metrics."
                ),
            },
            {
                "question": "Why doesn't Tformance have surveys yet?",
                "answer": (
                    "Because we are prioritizing GitHub-first delivery visibility first. "
                    "Surveys may come later, but they are not the wedge."
                ),
            },
        ],
    },
    "span": {
        "name": "Span",
        "slug": "span",
        "tagline": "AI code detection specialist",
        "website": "https://span.ai",
        "pricing_model": "enterprise",
        "pricing_range": "Enterprise (demo required)",
        "price_per_seat_low": 50,
        "price_per_seat_high": 100,
        "annual_cost_100_devs": 60000,
        "free_tier": None,
        "priority": "medium",
        "our_angle": "Delivery visibility plus AI-related context without enterprise-only rollout",
        "one_liner": "AI code detection specialist. Enterprise pricing.",
        "their_strengths": [
            "Deep code-level AI analysis",
            "Granular AI attribution models",
            "Enterprise compliance (SOC 2)",
            "Detailed code block detection",
        ],
        "our_advantages": [
            "Published transparent pricing",
            "Self-serve setup (5 minutes)",
            "PR-level detection is simpler",
            "Flat-rate, not enterprise pricing",
        ],
        "honest_gaps": [
            "They have code-level analysis (we do PR-level)",
            "They have deeper attribution models",
            "They have enterprise compliance",
        ],
        "best_for_them": "Enterprise teams needing code-level AI analysis",
        "best_for_us": "Teams wanting GitHub-first delivery visibility with directional AI signals",
        "features": {
            "ai_code_detection": True,
            "dora_metrics": "partial",
            "github": True,
            "jira": True,
            "soc2": True,
        },
        "seo": {
            "title": "Tformance vs Span: Delivery Visibility vs AI Detection",
            "description": (
                "Span alternative for teams that want delivery visibility, review bottleneck insight, "
                "and directional AI signals without enterprise pricing."
            ),
            "keywords": [
                "span ai alternative",
                "span app review",
                "AI code detection tools",
            ],
        },
        "faqs": [
            {
                "question": "Which gives smaller teams clearer delivery visibility, Tformance or Span?",
                "answer": (
                    "Span goes deeper on code-level attribution. Tformance focuses on delivery "
                    "visibility first and uses AI-related signals as supporting context."
                ),
            },
            {
                "question": "Is Span expensive?",
                "answer": ("Enterprise pricing—demo required. Tformance: $99-699/mo flat, published on site."),
            },
        ],
    },
    "workweave": {
        "name": "Workweave",
        "slug": "workweave",
        "tagline": "AI-focused PR analytics platform",
        "website": "https://workweave.ai",
        "pricing_model": "per-seat",
        "pricing_range": "$50/seat/mo",
        "price_per_seat_low": 50,
        "price_per_seat_high": 50,
        "annual_cost_100_devs": 60000,
        "free_tier": None,
        "priority": "medium",
        "our_angle": "Similar GitHub-first surface, clearer pricing, broader delivery story",
        "one_liner": "AI-focused PR analytics. $50/seat.",
        "their_strengths": [
            "Similar AI focus to us",
            "Jira integration available",
            "Per-seat for precise budgeting",
        ],
        "our_advantages": [
            "Flat-rate pricing saves money at scale",
            "No per-seat anxiety when hiring",
            "Predictable annual budgeting",
        ],
        "honest_gaps": [
            "They have Jira integration (ours coming)",
        ],
        "best_for_them": "Teams comfortable with per-seat pricing",
        "best_for_us": "Teams wanting flat-rate budget predictability",
        "features": {
            "ai_code_detection": True,
            "github": True,
            "jira": True,
        },
        "seo": {
            "title": "Tformance vs Workweave: Engineering Analytics Compared",
            "description": (
                "Workweave alternative: Tformance offers a broader delivery story with simpler "
                "flat-rate pricing for GitHub-first teams."
            ),
            "keywords": [
                "workweave alternative",
                "workweave pricing",
                "AI developer tools",
            ],
        },
        "faqs": [
            {
                "question": "Are Tformance and Workweave similar?",
                "answer": (
                    "They overlap on GitHub analytics, but Tformance emphasizes delivery "
                    "visibility first and keeps pricing simpler for smaller teams."
                ),
            },
            {
                "question": "Which is better for a 50-dev team?",
                "answer": "Tformance saves ~$26K/year (flat pricing). Features are similar.",
            },
        ],
    },
    "mesmer": {
        "name": "Mesmer",
        "slug": "mesmer",
        "tagline": "Engineering visibility and status automation",
        "website": "https://mesmer.ai",
        "pricing_model": "custom",
        "pricing_range": "Custom pricing",
        "price_per_seat_low": None,
        "price_per_seat_high": None,
        "annual_cost_100_devs": None,
        "free_tier": None,
        "priority": "low",
        "our_angle": "Metrics vs status automation",
        "one_liner": "Engineering visibility automation. Custom pricing.",
        "their_strengths": [
            "Automates status updates",
            "Reduces manual reporting",
            "Management visibility features",
        ],
        "our_advantages": [
            "Delivery visibility focus (not status automation)",
            "Published transparent pricing",
            "Delivery metrics, not reports",
        ],
        "honest_gaps": [
            "They automate status updates (we don't)",
        ],
        "best_for_them": "Teams wanting automated status updates",
        "best_for_us": "Teams that need delivery metrics, not status automation",
        "features": {
            "ai_code_detection": False,
            "github": True,
            "jira": True,
            "slack": True,
            "status_automation": True,
        },
        "seo": {
            "title": "Tformance vs Mesmer: Engineering Visibility Tools Compared",
            "description": (
                "Mesmer alternative: Tformance focuses on delivery metrics, not status "
                "automation. Compare approaches to engineering visibility."
            ),
            "keywords": [
                "mesmer alternative",
                "engineering visibility tools",
            ],
        },
        "faqs": [
            {
                "question": "Is Tformance a Mesmer alternative?",
                "answer": (
                    "Not directly. Mesmer automates status updates. "
                    "Tformance focuses on cycle time, review load, and PR flow."
                ),
            },
            {
                "question": "Can I use both Tformance and Mesmer?",
                "answer": (
                    "Yes. They solve different problems. Mesmer handles status automation; "
                    "Tformance handles delivery visibility."
                ),
            },
        ],
    },
    "nivara": {
        "name": "Nivara",
        "slug": "nivara",
        "tagline": "AI engineering manager (YC F25)",
        "website": "https://nivara.ai",
        "pricing_model": "demo",
        "pricing_range": "Demo required",
        "price_per_seat_low": None,
        "price_per_seat_high": None,
        "annual_cost_100_devs": None,
        "free_tier": None,
        "priority": "low",
        "our_angle": "Live delivery visibility today, not just an emerging vision",
        "one_liner": "AI engineering manager. YC F25.",
        "their_strengths": [
            "YC backing (F25 batch)",
            "AI-native approach",
        ],
        "our_advantages": [
            "Live customers and proven features",
            "Published transparent pricing",
            "Self-serve trial available",
        ],
        "honest_gaps": [
            "Limited comparison possible (very early stage)",
        ],
        "best_for_them": "Teams evaluating emerging tools",
        "best_for_us": "Teams wanting proven, transparent tooling",
        "features": {
            "ai_code_detection": True,
            "github": True,
        },
        "seo": {
            "title": "Tformance vs Nivara: AI Engineering Analytics Comparison",
            "description": (
                "Nivara alternative: Compare Tformance vs Nivara (YC F25). "
                "Both early stage, but with different approaches to engineering delivery visibility."
            ),
            "keywords": [
                "nivara alternative",
                "nivara ai",
                "AI engineering manager",
            ],
        },
        "faqs": [
            {
                "question": "Is Nivara a Tformance competitor?",
                "answer": (
                    "Yes, both sit in the engineering visibility space. Limited public info "
                    "on Nivara makes the comparison directional, not exhaustive."
                ),
            },
            {
                "question": "Which is further along?",
                "answer": (
                    "Both early stage. We have live alpha customers. "
                    "Nivara is YC F25. Judge by capabilities, not labels."
                ),
            },
        ],
    },
}


def get_competitor(slug: str) -> dict | None:
    """Get competitor data by slug."""
    return COMPETITORS.get(slug)


def get_all_competitors() -> dict:
    """Get all competitors."""
    return COMPETITORS


def get_competitors_by_priority(priority: str) -> list[dict]:
    """Get competitors filtered by priority."""
    return [c for c in COMPETITORS.values() if c.get("priority") == priority]


def calculate_savings(team_size: int, competitor_slug: str) -> dict | None:
    """Calculate annual savings vs a competitor.

    Returns:
        Dict with our_cost, their_cost, savings, percent_savings
    """
    competitor = COMPETITORS.get(competitor_slug)
    if not competitor:
        return None

    our_annual, our_tier = get_our_annual_cost(team_size)
    if our_annual is None:
        return None  # Enterprise - custom pricing

    # Calculate competitor cost
    their_low = competitor.get("price_per_seat_low")
    their_high = competitor.get("price_per_seat_high")

    if not their_low:
        return None  # Custom pricing, can't calculate

    # Use average of low/high for estimate
    their_per_seat = (their_low + their_high) / 2 if their_high else their_low
    their_annual = int(their_per_seat * team_size * 12)

    savings = their_annual - our_annual
    percent_savings = round((savings / their_annual) * 100) if their_annual > 0 else 0

    return {
        "our_cost": our_annual,
        "our_tier": our_tier,
        "their_cost": their_annual,
        "savings": savings,
        "percent_savings": percent_savings,
    }


# Feature comparison matrix for hub page
FEATURE_MATRIX = {
    "categories": [
        {
            "name": "AI Signals",
            "features": [
                {"key": "ai_code_detection", "label": "AI-related signals"},
                {"key": "ai_usage_correlation", "label": "AI correlation"},
            ],
        },
        {
            "name": "Core Metrics",
            "features": [
                {"key": "dora_metrics", "label": "DORA Metrics"},
                {"key": "pr_insights", "label": "PR Insights"},
            ],
        },
        {
            "name": "Developer Experience",
            "features": [
                {"key": "developer_surveys", "label": "Developer Surveys"},
                {"key": "gamified_surveys", "label": "Gamified Surveys"},
            ],
        },
        {
            "name": "Integrations",
            "features": [
                {"key": "github", "label": "GitHub"},
                {"key": "gitlab", "label": "GitLab"},
                {"key": "jira", "label": "Jira"},
                {"key": "slack", "label": "Slack"},
            ],
        },
        {
            "name": "Security",
            "features": [
                {"key": "soc2", "label": "SOC 2"},
            ],
        },
    ],
}


def get_feature_status_display(value) -> dict:
    """Convert feature value to display format.

    Returns:
        Dict with status, icon, label, css_class
    """
    if value is True or value == LIVE:
        return {
            "status": "live",
            "icon": "✅",
            "label": "Available",
            "css_class": "text-success",
        }
    elif value == SOON:
        return {
            "status": "soon",
            "icon": "🔜",
            "label": "Coming Soon",
            "css_class": "text-warning",
        }
    elif value == PLANNED:
        return {
            "status": "planned",
            "icon": "📋",
            "label": "Planned",
            "css_class": "text-info",
        }
    elif value == "partial":
        return {
            "status": "partial",
            "icon": "◐",
            "label": "Partial",
            "css_class": "text-warning",
        }
    else:
        return {
            "status": "no",
            "icon": "❌",
            "label": "Not Available",
            "css_class": "text-base-content/50",
        }

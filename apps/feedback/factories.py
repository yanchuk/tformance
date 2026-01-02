"""
Factory Boy factories for the feedback app.
"""

import factory
from factory.django import DjangoModelFactory

from apps.feedback.models import CATEGORY_CHOICES, CONTENT_TYPE_CHOICES, AIFeedback, LLMFeedback
from apps.integrations.factories import UserFactory
from apps.metrics.factories import TeamFactory, TeamMemberFactory


class AIFeedbackFactory(DjangoModelFactory):
    """Factory for creating AIFeedback instances."""

    class Meta:
        model = AIFeedback

    team = factory.SubFactory(TeamFactory)
    category = factory.Iterator([choice[0] for choice in CATEGORY_CHOICES])
    description = factory.Faker("paragraph")
    reported_by = factory.LazyAttribute(lambda obj: TeamMemberFactory(team=obj.team))
    status = "open"


class LLMFeedbackFactory(DjangoModelFactory):
    """Factory for creating LLMFeedback instances."""

    class Meta:
        model = LLMFeedback

    team = factory.SubFactory(TeamFactory)
    user = factory.SubFactory(UserFactory)
    content_type = factory.Iterator([choice[0] for choice in CONTENT_TYPE_CHOICES])
    content_id = factory.Sequence(lambda n: f"content_{n}")
    rating = factory.Faker("pybool")
    content_snapshot = factory.LazyFunction(lambda: {"summary": "Test LLM-generated content"})
    comment = ""
    prompt_version = ""

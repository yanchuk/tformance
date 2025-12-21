"""
Factory Boy factories for the feedback app.
"""

import factory
from factory.django import DjangoModelFactory

from apps.feedback.models import CATEGORY_CHOICES, AIFeedback
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

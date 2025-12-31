"""
Factory Boy factories for the notes app.
"""

import factory
from factory.django import DjangoModelFactory

from apps.metrics.factories import PullRequestFactory
from apps.notes.models import PRNote
from apps.users.models import CustomUser


class UserFactory(DjangoModelFactory):
    """Factory for creating CustomUser instances."""

    class Meta:
        model = CustomUser

    username = factory.Sequence(lambda n: f"user{n}@example.com")
    email = factory.LazyAttribute(lambda obj: obj.username)
    password = factory.PostGenerationMethodCall("set_password", "testpass123")


class PRNoteFactory(DjangoModelFactory):
    """Factory for creating PRNote instances."""

    class Meta:
        model = PRNote

    user = factory.SubFactory(UserFactory)
    pull_request = factory.SubFactory(PullRequestFactory)
    content = factory.Faker("paragraph", nb_sentences=2)
    flag = factory.Iterator(["", "", "false_positive", "review_later", "important", "concern"])
    is_resolved = False
    resolved_at = None

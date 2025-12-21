"""
Base imports and utilities for metrics models.

All models in this package inherit from BaseTeamModel for team scoping.
"""

from django.db import models

from apps.teams.models import BaseTeamModel

__all__ = ["models", "BaseTeamModel"]

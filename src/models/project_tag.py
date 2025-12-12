"""
ProjectTag data model for OneTaskAtATime application.

Project tags provide flat organization without nested hierarchies.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ProjectTag:
    """
    Represents a project or area of focus for organizing tasks.

    Unlike traditional project hierarchies, ProjectTags are flat and can be
    applied to multiple tasks. Tasks can have multiple ProjectTags.

    Attributes:
        id: Unique identifier (None for unsaved tags)
        name: Project tag name (e.g., "Website Redesign", "Personal Development")
        description: Optional project description
        color: Hex color code for UI display (e.g., "#FF5733")
        created_at: Creation timestamp
        updated_at: Last modification timestamp
    """

    name: str
    id: Optional[int] = None
    description: Optional[str] = None
    color: Optional[str] = None  # Hex color code
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __str__(self) -> str:
        """String representation of project tag."""
        return self.name

    def __repr__(self) -> str:
        """Developer representation of project tag."""
        return f"ProjectTag(id={self.id}, name='{self.name}', color='{self.color}')"

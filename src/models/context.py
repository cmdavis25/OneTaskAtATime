"""
Context data model for OneTaskAtATime application.

Contexts represent work environments or tools (e.g., @computer, @phone, @home).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Context:
    """
    Represents a work environment or tool context.

    In GTD, contexts help filter tasks by what you can do in your current situation.
    Examples: @computer, @phone, @errands, @home, @office

    Attributes:
        id: Unique identifier (None for unsaved contexts)
        name: Context name (e.g., "@computer")
        description: Optional explanation of context
        created_at: Creation timestamp
        updated_at: Last modification timestamp
    """

    name: str
    id: Optional[int] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __str__(self) -> str:
        """String representation of context."""
        return self.name

    def __repr__(self) -> str:
        """Developer representation of context."""
        return f"Context(id={self.id}, name='{self.name}')"

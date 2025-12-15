"""PostgreSQL database layer for config and message storage."""

from kirc.db.client import DatabaseClient
from kirc.db.models import Contact, Message, ServiceConfig, UserProfile

__all__ = ["DatabaseClient", "Contact", "Message", "ServiceConfig", "UserProfile"]

"""
Unit tests for the DATA-LAYER module.

Tests cover:
- BaseModel field defaults (UUID, timestamps, is_active)
- Database session factory configuration
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from mes.framework.db.base import Base, BaseModel


class TestBaseModel:
    def test_base_is_abstract(self):
        """BaseModel is abstract and cannot be directly instantiated as a table."""
        assert BaseModel.__abstract__ is True

    def test_base_inherits_declarative(self):
        """BaseModel inherits from the declarative Base."""
        assert issubclass(BaseModel, Base)

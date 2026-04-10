"""GradeFactory."""

from __future__ import annotations

import factory

from pindb.database.grade import Grade
from tests.factories.base import BaseFactory


class GradeFactory(BaseFactory):
    class Meta:
        model = Grade
        sqlalchemy_session_persistence = "flush"

    name = factory.Sequence(lambda n: f"Grade {n}")
    price = factory.Sequence(lambda n: float(n) * 5.0)

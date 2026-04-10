"""UserFactory and AdminUserFactory."""

from __future__ import annotations

import factory

from pindb.auth import hash_password
from pindb.database.user import User
from tests.factories.base import BaseFactory


class UserFactory(BaseFactory):
    class Meta:
        model = User
        sqlalchemy_session_persistence = "flush"

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    hashed_password = factory.LazyFunction(lambda: hash_password("testpass123"))
    is_admin = False


class AdminUserFactory(UserFactory):
    username = factory.Sequence(lambda n: f"admin{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    is_admin = True

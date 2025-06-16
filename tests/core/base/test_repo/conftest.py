from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine

from .modesl_for_test import (
    TestUser,
    TestProfile,
    TestCategory,
    TestPost,
    TestTag,
    TestComment,
    post_tags_table,
)
from core.base.repo import BaseRepository
from core.base.models import BaseModel

from contextlib import asynccontextmanager

@asynccontextmanager
async def create_models_for_test(async_session):
    engine: AsyncEngine = async_session.bind
    tables = [
        TestUser.__table__,
        TestProfile.__table__,
        TestCategory.__table__,
        TestPost.__table__,
        TestTag.__table__,
        TestComment.__table__,
        post_tags_table
    ]

    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: BaseModel.metadata.create_all(
            bind=sync_conn, tables=tables, checkfirst=True))

    try:
        yield
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: BaseModel.metadata.drop_all(
                bind=sync_conn, tables=tables, checkfirst=True))

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_test_models(async_session):
    async with create_models_for_test(async_session):
        yield

@pytest.fixture
def user_factory(async_session):
    from .factories import TestUserFactory
    TestUserFactory._meta.sqlalchemy_session = async_session  # noqa
    return TestUserFactory


@pytest.fixture
def post_factory(async_session):
    from .factories import TestPostFactory
    TestPostFactory._meta.sqlalchemy_session = async_session  # noqa
    return TestPostFactory


@pytest.fixture
def category_factory(async_session):
    from .factories import TestCategoryFactory
    TestCategoryFactory._meta.sqlalchemy_session = async_session  # noqa
    return TestCategoryFactory


@pytest.fixture
def tag_factory(async_session):
    from .factories import TestTagFactory
    TestTagFactory._meta.sqlalchemy_session = async_session  # noqa
    return TestTagFactory


@pytest.fixture
def comment_factory(async_session):
    from .factories import TestCommentFactory
    TestCommentFactory._meta.sqlalchemy_session = async_session  # noqa
    return TestCommentFactory


@pytest.fixture
def profile_factory(async_session):
    from .factories import TestProfileFactory
    TestProfileFactory._meta.sqlalchemy_session = async_session  # noqa
    return TestProfileFactory


@pytest.fixture
def post_create_schema():
    from .shemes_for_test import TestPostCreate
    return TestPostCreate


@pytest.fixture
def post_update_schema():
    from .shemes_for_test import TestPostUpdate
    return TestPostUpdate


@pytest.fixture
def post_repo(async_session):
    return BaseRepository(TestPost, async_session)

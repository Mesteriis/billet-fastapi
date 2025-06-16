from __future__ import annotations

import uuid
from datetime import datetime, date, timedelta

from async_factory_boy.factory.sqlalchemy import AsyncSQLAlchemyFactory
from factory import Faker, SubFactory, LazyAttribute, Sequence, RelatedFactory, LazyFunction, Factory
from pytz import utc

from .enums import PostStatus, Priority
from .modesl_for_test import (
    TestUser,
    TestProfile,
    TestCategory,
    TestPost,
    TestTag,
    TestComment,
)
from .shemes_for_test import TestPostCreate, TestPostUpdate


class TestUserFactory(AsyncSQLAlchemyFactory):
    """
    Фабрика для модели TestUser.
    """

    class Meta:
        model = TestUser
        sqlalchemy_session_persistence = "commit"
        sqlalchemy_session = None

    username = Sequence(lambda n: f"user_{n}")
    email = Faker("email")
    full_name = Faker("name")
    hashed_password = Faker("password")
    is_active = True
    is_superuser = False
    is_verified = False
    avatar_url = Faker("image_url")
    bio = Faker("paragraph")
    last_login_at = LazyAttribute(lambda _: datetime.now(tz=utc) - timedelta(days=1))
    email_verified_at = None
    profile = RelatedFactory("TestProfileFactory", factory_related_name='user')


class TestProfileFactory(AsyncSQLAlchemyFactory):
    """
    Фабрика для модели TestProfile.
    """

    class Meta:
        model = TestProfile
        sqlalchemy_session_persistence = "commit"
        sqlalchemy_session = None

    phone = Faker("phone_number")
    website = Faker("url")
    address = Faker("address")
    city = Faker("city")
    country = Faker("country")
    postal_code = Faker("postcode")
    timezone = Faker("timezone")
    language = "en"
    preferences = {}
    user = SubFactory(TestUserFactory)


class TestCategoryFactory(AsyncSQLAlchemyFactory):
    """
    Фабрика для модели TestCategory.
    """

    class Meta:
        model = TestCategory
        sqlalchemy_session_persistence = "commit"
        sqlalchemy_session = None

    name = Sequence(lambda n: f"Category {n}")
    slug = LazyAttribute(lambda obj: obj.name.lower().replace(" ", "-"))
    description = Faker("sentence")
    level = 0
    sort_order = 0
    posts_count = 0
    parent = None


class TestPostFactory(AsyncSQLAlchemyFactory):
    """
    Фабрика для модели TestPost.
    """

    class Meta:
        model = TestPost
        sqlalchemy_session_persistence = "commit"
        sqlalchemy_session = None

    title = Faker("sentence")
    slug = Sequence(lambda n: f"post-{n}")
    content = Faker("text")
    excerpt = Faker("sentence")
    status = "draft"
    priority = "medium"
    views_count = 0
    likes_count = 0
    rating = None
    published_at = LazyAttribute(lambda _: datetime.now(tz=utc))
    scheduled_at = LazyAttribute(lambda _: datetime.now().date())
    is_featured = False
    is_premium = False
    allow_comments = True
    extra_metadata = {}
    seo_data = {}
    search_vector = None
    author = SubFactory(TestUserFactory)
    category = SubFactory(TestCategoryFactory)


class TestTagFactory(AsyncSQLAlchemyFactory):
    """
    Фабрика для модели TestTag.
    """

    class Meta:
        model = TestTag
        sqlalchemy_session_persistence = "commit"
        sqlalchemy_session = None

    name = Sequence(lambda n: f"tag-{n}")
    color = Faker("hex_color")
    usage_count = 0


class TestCommentFactory(AsyncSQLAlchemyFactory):
    """
    Фабрика для модели TestComment.
    """

    class Meta:
        model = TestComment
        sqlalchemy_session_persistence = "commit"
        sqlalchemy_session = None

    content = Faker("paragraph")
    level = 0
    is_approved = True
    is_spam = False
    likes_count = 0
    post = SubFactory(TestPostFactory)
    author = SubFactory(TestUserFactory)
    parent = None


class TestPostCreateFactory(Factory):
    """Фабрика для создания Pydantic схемы TestPostCreate."""

    class Meta:
        model = TestPostCreate

    title = Faker("sentence", nb_words=6)
    slug = LazyAttribute(lambda o: o.title.lower().replace(" ", "-"))
    content = Faker("text", max_nb_chars=1500)
    excerpt = Faker("text", max_nb_chars=250)
    status = PostStatus.DRAFT
    priority = Priority.MEDIUM
    published_at = LazyFunction(lambda: datetime.now(tz=utc))
    scheduled_at = LazyFunction(lambda: date.today() + timedelta(days=1))
    is_featured = False
    is_premium = False
    allow_comments = True
    extra_metadata = LazyFunction(lambda: {"keywords": ["test", "pydantic"]})
    seo_data = LazyFunction(lambda: {"title": "SEO Title", "description": "SEO Description"})
    author_id = LazyFunction(uuid.uuid4)
    category_id = LazyFunction(uuid.uuid4)


class TestPostUpdateFactory(Factory):
    """Фабрика для создания Pydantic схемы TestPostUpdate."""

    class Meta:
        model = TestPostUpdate

    title = Faker("sentence", nb_words=6)
    content = Faker("text", max_nb_chars=1500)
    excerpt = Faker("text", max_nb_chars=250)
    status = PostStatus.PUBLISHED
    priority = Priority.HIGH
    views_count = Faker("random_int", min=0, max=500)
    likes_count = Faker("random_int", min=0, max=100)
    rating = Faker("pyfloat", positive=True, max_value=5.0)
    published_at = LazyFunction(lambda: datetime.now(tz=utc))
    scheduled_at = LazyFunction(lambda: date.today())
    is_featured = Faker("boolean")
    is_premium = Faker("boolean")
    allow_comments = Faker("boolean")
    extra_metadata = LazyFunction(lambda: {"editors_pick": True})
    seo_data = LazyFunction(lambda: {"canonical": "https://example.com/post"})
    category_id = LazyFunction(uuid.uuid4)

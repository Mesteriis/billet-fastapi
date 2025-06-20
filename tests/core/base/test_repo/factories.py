from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Any

import faker
from async_factory_boy.factory.sqlalchemy import AsyncSQLAlchemyFactory
from factory.base import Factory
from factory.declarations import LazyAttribute, LazyFunction, RelatedFactory, Sequence, SubFactory
from factory.faker import Faker
from pytz import utc

# Создаем экземпляр faker для генерации данных
fake = faker.Faker()

from .enums import PostStatus, Priority
from .modesl_for_test import TestCategory, TestComment, TestPost, TestProfile, TestTag, TestUser
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
    is_verified = Faker("boolean", chance_of_getting_true=60)
    avatar_url = Faker("image_url")
    bio = Faker("paragraph")
    last_login_at = LazyAttribute(lambda _: datetime.now(tz=utc) - timedelta(days=1))
    email_verified_at = LazyAttribute(lambda obj: datetime.now(tz=utc) if obj.is_verified else None)


class TestProfileFactory(AsyncSQLAlchemyFactory):
    """
    Фабрика для модели TestProfile.
    """

    class Meta:
        model = TestProfile
        sqlalchemy_session_persistence = "commit"
        sqlalchemy_session = None

    phone = Faker("bothify", text="+#-###-###-####")  # Максимум 15 символов
    website = Faker("url")
    address = Faker("address")
    city = LazyFunction(lambda: fake.city()[:95])  # Ограничиваем до 95 символов
    country = LazyFunction(lambda: fake.country()[:95])  # Ограничиваем до 95 символов
    postal_code = LazyFunction(lambda: fake.postcode()[:15])  # Ограничиваем до 15 символов
    timezone = Faker("timezone")
    language = LazyFunction(lambda: fake.language_code()[:8])  # Ограничиваем до 8 символов
    preferences = LazyFunction(
        lambda: {
            "notifications": True,
            "theme": "light",
            "language": "en",
        }
    )
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
    slug = LazyAttribute(lambda obj: obj.name.lower().replace(" ", "-")[:95])  # Ограничиваем до 95 символов
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

    title = Faker("sentence", nb_words=8)
    slug = Sequence(lambda n: f"post-{n}")
    content = Faker("text", max_nb_chars=2000)
    excerpt = Faker("text", max_nb_chars=300)
    status = Faker("random_element", elements=[PostStatus.DRAFT, PostStatus.PUBLISHED, PostStatus.ARCHIVED])
    priority = Faker("random_element", elements=[Priority.LOW, Priority.MEDIUM, Priority.HIGH])
    views_count = Faker("random_int", min=0, max=1000)
    likes_count = Faker("random_int", min=0, max=100)
    rating = Faker("pyfloat", left_digits=1, right_digits=2, positive=True, max_value=5.0)
    published_at = LazyAttribute(lambda obj: datetime.now(tz=utc) if obj.status == PostStatus.PUBLISHED else None)
    scheduled_at = LazyAttribute(lambda _: datetime.now().date() + timedelta(days=1))
    is_featured = Faker("boolean", chance_of_getting_true=20)
    is_premium = Faker("boolean", chance_of_getting_true=10)
    allow_comments = Faker("boolean", chance_of_getting_true=80)
    extra_metadata = LazyFunction(lambda: {"keywords": ["test", "sample"], "featured": False})
    seo_data = LazyFunction(lambda: {"title": "SEO Title", "description": "SEO Description"})
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
    color = Faker("hex_color")  # Уже ограничен до 7 символов
    usage_count = 0


class TestCommentFactory(AsyncSQLAlchemyFactory):
    """
    Фабрика для модели TestComment.
    """

    class Meta:
        model = TestComment
        sqlalchemy_session_persistence = "commit"
        sqlalchemy_session = None

    content = Faker("text", max_nb_chars=500)
    level = 0
    is_approved = Faker("boolean", chance_of_getting_true=90)
    is_spam = Faker("boolean", chance_of_getting_true=5)
    likes_count = Faker("random_int", min=0, max=50)
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


class UserFactory(AsyncSQLAlchemyFactory):
    """Фабрика для создания тестовых пользователей."""

    class Meta:
        model = TestUser
        sqlalchemy_session_persistence = "commit"

    id = LazyFunction(lambda: uuid.uuid4())
    username = LazyAttribute(lambda obj: f"user_{fake.uuid4()[:8]}")
    email = LazyAttribute(lambda obj: f"{obj.username}@example.com")
    full_name = Faker("name", locale="ru_RU")
    hashed_password = Faker("password", length=12)
    is_active = Faker("boolean", chance_of_getting_true=85)
    is_superuser = Faker("boolean", chance_of_getting_true=5)
    is_verified = Faker("boolean", chance_of_getting_true=60)
    avatar_url = Faker("image_url", width=200, height=200)
    bio = Faker("text", max_nb_chars=200, locale="ru_RU")
    last_login_at = LazyFunction(lambda: fake.date_time_this_year(tzinfo=utc))
    email_verified_at = LazyFunction(lambda: fake.date_time_this_year(tzinfo=utc))


class CategoryFactory(AsyncSQLAlchemyFactory):
    """Фабрика для создания тестовых категорий."""

    class Meta:
        model = TestCategory
        sqlalchemy_session_persistence = "commit"

    id = LazyFunction(lambda: uuid.uuid4())
    name = Faker("word", locale="ru_RU")
    slug = LazyAttribute(lambda obj: f"{obj.name.lower()}-{fake.uuid4()[:6]}")
    description = Faker("text", max_nb_chars=300, locale="ru_RU")
    level = Faker("random_int", min=0, max=3)
    sort_order = Faker("random_int", min=0, max=100)
    posts_count = Faker("random_int", min=0, max=50)


class TagFactory(AsyncSQLAlchemyFactory):
    """Фабрика для создания тестовых тегов."""

    class Meta:
        model = TestTag
        sqlalchemy_session_persistence = "commit"

    id = LazyFunction(lambda: uuid.uuid4())
    name = Faker("word", locale="ru_RU")
    color = Faker("hex_color")
    usage_count = Faker("random_int", min=0, max=100)


class PostFactory(AsyncSQLAlchemyFactory):
    """Фабрика для создания тестовых постов."""

    class Meta:
        model = TestPost
        sqlalchemy_session_persistence = "commit"

    id = LazyFunction(lambda: uuid.uuid4())
    title = Faker("sentence", nb_words=5, locale="ru_RU")
    slug = LazyAttribute(lambda obj: f"post-{fake.uuid4()[:8]}")
    content = Faker("text", max_nb_chars=1000, locale="ru_RU")
    excerpt = Faker("text", max_nb_chars=200, locale="ru_RU")
    status = Faker("random_element", elements=[PostStatus.DRAFT, PostStatus.PUBLISHED, PostStatus.ARCHIVED])
    priority = Faker("random_element", elements=[Priority.LOW, Priority.MEDIUM, Priority.HIGH])
    views_count = Faker("random_int", min=0, max=10000)
    likes_count = Faker("random_int", min=0, max=500)
    rating = Faker("pyfloat", left_digits=1, right_digits=1, positive=True, max_value=5.0)
    published_at = LazyFunction(lambda: fake.date_time_this_year(tzinfo=utc))
    scheduled_at = LazyFunction(lambda: fake.date_this_year())
    is_featured = Faker("boolean", chance_of_getting_true=20)
    is_premium = Faker("boolean", chance_of_getting_true=10)
    allow_comments = Faker("boolean", chance_of_getting_true=80)
    extra_metadata = LazyFunction(
        lambda: {
            "keywords": fake.words(nb=3),
            "author_notes": fake.text(max_nb_chars=100),
            "reading_time": fake.random_int(min=1, max=30),
        }
    )
    seo_data = LazyFunction(
        lambda: {
            "meta_title": fake.sentence(nb_words=4),
            "meta_description": fake.text(max_nb_chars=160),
            "canonical_url": fake.url(),
        }
    )

    # Связи - будут назначены в тестах
    author = SubFactory(UserFactory)
    category = SubFactory(CategoryFactory)


class CommentFactory(AsyncSQLAlchemyFactory):
    """Фабрика для создания тестовых комментариев."""

    class Meta:
        model = TestComment
        sqlalchemy_session_persistence = "commit"

    id = LazyFunction(lambda: uuid.uuid4())
    content = Faker("text", max_nb_chars=500, locale="ru_RU")
    level = Faker("random_int", min=0, max=3)
    is_approved = Faker("boolean", chance_of_getting_true=70)
    is_spam = Faker("boolean", chance_of_getting_true=5)
    likes_count = Faker("random_int", min=0, max=50)

    # Связи - будут назначены в тестах
    post = SubFactory(PostFactory)
    author = SubFactory(UserFactory)


class ProfileFactory(AsyncSQLAlchemyFactory):
    """Фабрика для создания тестовых профилей."""

    class Meta:
        model = TestProfile
        sqlalchemy_session_persistence = "commit"

    id = LazyFunction(lambda: uuid.uuid4())
    phone = Faker("phone_number", locale="ru_RU")
    website = Faker("url")
    address = Faker("address", locale="ru_RU")
    city = Faker("city", locale="ru_RU")
    country = Faker("country", locale="ru_RU")
    postal_code = Faker("postcode", locale="ru_RU")
    timezone = Faker("timezone")
    language = Faker("random_element", elements=["ru", "en", "de", "fr"])
    preferences = LazyFunction(
        lambda: {
            "theme": fake.random_element(elements=["light", "dark"]),
            "notifications": fake.boolean(),
            "language": fake.language_code(),
        }
    )

    # Связь - будет назначена в тестах
    user = SubFactory(UserFactory)

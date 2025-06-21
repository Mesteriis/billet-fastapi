"""Create users tables

Revision ID: 38e17bc878df
Revises: 
Create Date: 2025-06-21 14:16:00.693123

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '38e17bc878df'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаем таблицу users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        
        # Основные учетные данные
        sa.Column('username', sa.String(length=50), nullable=False, comment='Уникальное имя пользователя'),
        sa.Column('email', sa.String(length=255), nullable=False, comment='Email адрес пользователя'),
        sa.Column('password_hash', sa.String(length=255), nullable=False, comment='Хеш пароля пользователя'),
        
        # Основные персональные данные
        sa.Column('first_name', sa.String(length=100), nullable=True, comment='Имя пользователя'),
        sa.Column('last_name', sa.String(length=100), nullable=True, comment='Фамилия пользователя'),
        sa.Column('avatar_url', sa.String(length=500), nullable=True, comment='URL аватара пользователя'),
        
        # Роли и статусы
        sa.Column('role', sa.String(length=20), nullable=False, server_default=sa.text("'user'"), comment='Роль пользователя'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default=sa.text("'pending'"), comment='Статус пользователя'),
        
        # Флаги активности
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true'), comment='Активен ли пользователь'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false'), comment='Подтвержден ли email пользователя'),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default=sa.text('false'), comment='Является ли пользователь суперпользователем'),
        
        # Метаданные активности
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True, comment='Время последнего входа'),
        sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True, comment='Время подтверждения email'),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True, comment='Время последней активности'),
        
        # Ограничения
        sa.UniqueConstraint('username', name='uq_users_username'),
        sa.UniqueConstraint('email', name='uq_users_email'),
    )
    
    # Создаем индексы для users
    op.create_index('ix_users_username', 'users', ['username'])
    op.create_index('ix_users_email', 'users', ['email'])
    
    # Создаем таблицу user_profiles
    op.create_table(
        'user_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        
        # Связь с пользователем
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, comment='ID пользователя'),
        
        # Дополнительная персональная информация
        sa.Column('bio', sa.Text(), nullable=True, comment='Биография пользователя'),
        sa.Column('phone', sa.String(length=20), nullable=True, comment='Телефон пользователя'),
        sa.Column('birth_date', sa.Date(), nullable=True, comment='Дата рождения'),
        sa.Column('location', sa.String(length=255), nullable=True, comment='Местоположение пользователя'),
        sa.Column('website', sa.String(length=500), nullable=True, comment='Веб-сайт пользователя'),
        
        # Настройки локализации
        sa.Column('timezone', sa.String(length=50), nullable=False, server_default=sa.text("'UTC'"), comment='Временная зона пользователя'),
        sa.Column('language', sa.String(length=5), nullable=False, server_default=sa.text("'en'"), comment='Язык интерфейса'),
        
        # Настройки интерфейса
        sa.Column('theme', sa.String(length=10), nullable=False, server_default=sa.text("'light'"), comment='Тема интерфейса'),
        
        # Настройки уведомлений
        sa.Column('notifications_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true'), comment='Включены ли уведомления'),
        sa.Column('notification_level', sa.String(length=20), nullable=False, server_default=sa.text("'all'"), comment='Уровень уведомлений'),
        sa.Column('email_notifications', sa.Boolean(), nullable=False, server_default=sa.text('true'), comment='Email уведомления'),
        sa.Column('push_notifications', sa.Boolean(), nullable=False, server_default=sa.text('true'), comment='Push уведомления'),
        
        # Настройки приватности
        sa.Column('public_profile', sa.Boolean(), nullable=False, server_default=sa.text('true'), comment='Публичный ли профиль'),
        sa.Column('show_email', sa.Boolean(), nullable=False, server_default=sa.text('false'), comment='Показывать ли email в профиле'),
        sa.Column('show_phone', sa.Boolean(), nullable=False, server_default=sa.text('false'), comment='Показывать ли телефон в профиле'),
        
        # Ограничения
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_user_profiles_user_id', ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', name='uq_user_profiles_user_id'),
    )
    
    # Создаем индекс для user_profiles
    op.create_index('ix_user_profiles_user_id', 'user_profiles', ['user_id'])


def downgrade() -> None:
    # Удаляем таблицы в обратном порядке
    op.drop_table('user_profiles')
    op.drop_table('users')

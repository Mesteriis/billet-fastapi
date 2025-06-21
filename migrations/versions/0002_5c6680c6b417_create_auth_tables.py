"""Create auth tables

Revision ID: 5c6680c6b417
Revises: 38e17bc878df
Create Date: 2025-06-21 14:17:04.209121

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5c6680c6b417'
down_revision: Union[str, None] = '38e17bc878df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаем таблицу refresh_tokens
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        
        # Связь с пользователем
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, comment='ID пользователя'),
        
        # Данные токена
        sa.Column('token_hash', sa.String(length=255), nullable=False, comment='Хеш refresh токена'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False, comment='Время истечения токена'),
        
        # Метаданные устройства и сессии
        sa.Column('device_info', sa.Text(), nullable=True, comment='Информация об устройстве (User-Agent)'),
        sa.Column('ip_address', sa.String(length=45), nullable=True, comment='IP адрес клиента'),
        sa.Column('device_fingerprint', sa.String(length=255), nullable=True, comment='Отпечаток устройства'),
        
        # Флаги состояния
        sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default=sa.text('false'), comment='Отозван ли токен'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True, comment='Время последнего использования'),
        
        # Ограничения
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_refresh_tokens_user_id', ondelete='CASCADE'),
        sa.UniqueConstraint('token_hash', name='uq_refresh_tokens_token_hash'),
    )
    
    # Создаем индексы для refresh_tokens
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'])
    op.create_index('ix_refresh_tokens_token_hash', 'refresh_tokens', ['token_hash'])
    op.create_index('ix_refresh_tokens_expires_at', 'refresh_tokens', ['expires_at'])
    
    # Создаем таблицу user_sessions
    op.create_table(
        'user_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        
        # Связь с пользователем
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, comment='ID пользователя'),
        
        # Данные сессии
        sa.Column('session_id', sa.String(length=255), nullable=False, comment='Уникальный ID сессии'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False, comment='Время истечения сессии'),
        
        # Данные сессии в JSON
        sa.Column('data', postgresql.JSON(), nullable=False, server_default=sa.text("'{}'"), comment='Данные сессии в JSON формате'),
        
        # Метаданные сессии
        sa.Column('ip_address', sa.String(length=45), nullable=True, comment='IP адрес клиента'),
        sa.Column('user_agent', sa.Text(), nullable=True, comment='User-Agent браузера'),
        sa.Column('csrf_token', sa.String(length=255), nullable=True, comment='CSRF токен для защиты'),
        
        # Флаги состояния
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true'), comment='Активна ли сессия'),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), comment='Время последней активности'),
        
        # Ограничения
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_user_sessions_user_id', ondelete='CASCADE'),
        sa.UniqueConstraint('session_id', name='uq_user_sessions_session_id'),
    )
    
    # Создаем индексы для user_sessions
    op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('ix_user_sessions_session_id', 'user_sessions', ['session_id'])
    op.create_index('ix_user_sessions_expires_at', 'user_sessions', ['expires_at'])
    
    # Создаем таблицу orbital_tokens
    op.create_table(
        'orbital_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        
        # Связь с пользователем
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, comment='ID пользователя'),
        
        # Данные токена
        sa.Column('token_hash', sa.String(length=255), nullable=False, comment='Хеш токена'),
        sa.Column('token_type', sa.String(length=50), nullable=False, comment='Тип токена (email_verification, password_reset, etc.)'),
        sa.Column('purpose', sa.String(length=255), nullable=False, comment='Назначение токена'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False, comment='Время истечения токена'),
        
        # Метаданные
        sa.Column('token_metadata', postgresql.JSON(), nullable=False, server_default=sa.text("'{}'"), comment='Дополнительные данные токена в JSON формате'),
        sa.Column('ip_address', sa.String(length=45), nullable=True, comment='IP адрес при создании токена'),
        
        # Флаги состояния
        sa.Column('is_used', sa.Boolean(), nullable=False, server_default=sa.text('false'), comment='Использован ли токен'),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True, comment='Время использования токена'),
        
        # Ограничения
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_orbital_tokens_user_id', ondelete='CASCADE'),
        sa.UniqueConstraint('token_hash', name='uq_orbital_tokens_token_hash'),
    )
    
    # Создаем индексы для orbital_tokens
    op.create_index('ix_orbital_tokens_user_id', 'orbital_tokens', ['user_id'])
    op.create_index('ix_orbital_tokens_token_hash', 'orbital_tokens', ['token_hash'])
    op.create_index('ix_orbital_tokens_token_type', 'orbital_tokens', ['token_type'])
    op.create_index('ix_orbital_tokens_expires_at', 'orbital_tokens', ['expires_at'])


def downgrade() -> None:
    # Удаляем таблицы в обратном порядке
    op.drop_table('orbital_tokens')
    op.drop_table('user_sessions')
    op.drop_table('refresh_tokens')

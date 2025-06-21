"""Authentication Application Interfaces.

This module defines Protocol interfaces for the authentication application
to reduce coupling between modules and avoid circular imports.

The interfaces provide contracts for:
- JWT token payloads and management
- User session handling
- Authentication results and attempts
- Security event logging
- Two-factor authentication
- Password reset and email verification workflows

Example:
    Using token payload interface::

        from apps.auth.interfaces import TokenPayload

        def create_jwt_token(payload: TokenPayload) -> str:
            # Token creation logic using payload interface
            return jwt.encode({
                "user_id": str(payload.user_id),
                "username": payload.username,
                "exp": payload.expires_at
            })

    Implementing session management::

        from apps.auth.interfaces import SessionData

        class UserSession:
            def __init__(self, session: SessionData):
                self.session = session

            def is_valid(self) -> bool:
                return self.session.is_valid

    Security event logging::

        from apps.auth.interfaces import SecurityEvent

        async def log_login_attempt(event: SecurityEvent):
            if event.severity == "critical":
                await send_security_alert(event)

Note:
    These interfaces use Protocol typing to provide structural subtyping,
    allowing any class that implements the required methods and attributes
    to satisfy the interface contract without explicit inheritance.
"""

import uuid
from datetime import datetime
from typing import Any, Literal, Optional, Protocol, Union

# Type aliases for SQLAlchemy compatibility
IdType = Union[uuid.UUID, Any]  # Support Mapped[UUID] and UUID
StrType = Union[str, Any]  # Support Mapped[str] and str
BoolType = Union[bool, Any]  # Support Mapped[bool] and bool
DateType = Union[datetime, Any]  # Support Mapped[datetime] and datetime

# Literals for token types and events
TokenTypeType = Union[Literal["access", "refresh"], Any]
EventSeverityType = Union[Literal["low", "medium", "high", "critical"], Any]
TwoFAMethodType = Union[Literal["totp", "sms", "email"], Any]


class TokenPayload(Protocol):
    """JWT token payload interface.

    Contains essential user information embedded in JWT tokens
    for authentication and authorization purposes.

    Attributes:
        user_id (IdType): Unique user identifier
        username (StrType): User's username
        email (StrType): User's email address
        role (StrType): User's role in the system
        permissions (list[str]): List of user permissions
        device_fingerprint (Optional[StrType]): Device identification
        issued_at (DateType): Token creation timestamp
        expires_at (DateType): Token expiration timestamp

    Example:
        Creating a token payload::

            class JWTPayload:
                def __init__(self, user_id: uuid.UUID, username: str, email: str):
                    self.user_id = user_id
                    self.username = username
                    self.email = email
                    self.role = "user"
                    self.permissions = ["read", "write"]
                    self.issued_at = datetime.utcnow()
                    self.expires_at = datetime.utcnow() + timedelta(hours=1)

                @property
                def is_expired(self) -> bool:
                    return datetime.utcnow() > self.expires_at
    """

    user_id: IdType
    username: StrType
    email: StrType
    role: StrType
    permissions: list[str]
    device_fingerprint: Optional[StrType]

    # Timestamps
    issued_at: DateType
    expires_at: DateType

    @property
    def is_expired(self) -> bool:
        """Check if token is expired.

        Returns:
            bool: True if token has expired
        """
        ...


class RefreshTokenData(Protocol):
    """Refresh token interface.

    Used for refreshing access tokens without requiring
    user re-authentication.

    Attributes:
        id (IdType): Unique token identifier
        user_id (IdType): Associated user ID
        token_hash (StrType): Hashed token value
        expires_at (DateType): Token expiration time
        is_revoked (BoolType): Whether token is revoked
        device_info (Optional[StrType]): Device information
        ip_address (Optional[StrType]): Client IP address
        device_fingerprint (Optional[StrType]): Device fingerprint
        last_used_at (Optional[DateType]): Last usage timestamp

    Example:
        Refresh token validation::

            def validate_refresh_token(token: RefreshTokenData) -> bool:
                if not token.is_valid:
                    return False
                if token.is_revoked:
                    return False
                return True

        Revoking a token::

            def revoke_token(token: RefreshTokenData):
                token.revoke()
                # Token is now invalid for future use
    """

    id: IdType
    user_id: IdType
    token_hash: StrType
    expires_at: DateType
    is_revoked: BoolType

    # Device metadata
    device_info: Optional[StrType]
    ip_address: Optional[StrType]
    device_fingerprint: Optional[StrType]
    last_used_at: Optional[DateType]

    @property
    def is_valid(self) -> bool:
        """Check if token is valid.

        Returns:
            bool: True if token is valid and not expired
        """
        ...

    def revoke(self) -> None:
        """Revoke the token."""
        ...


class SessionData(Protocol):
    """User session interface.

    Contains information about user web sessions including
    session data, CSRF protection, and metadata.

    Attributes:
        id (uuid.UUID): Session identifier
        user_id (uuid.UUID): Associated user ID
        session_id (str): Session string identifier
        expires_at (datetime): Session expiration
        is_active (bool): Whether session is active
        data (dict[str, Any]): Session data storage
        csrf_token (Optional[str]): CSRF protection token
        ip_address (Optional[str]): Client IP address
        user_agent (Optional[str]): Client user agent
        last_activity_at (datetime): Last activity timestamp

    Example:
        Session data management::

            def store_user_preference(session: SessionData, key: str, value: Any):
                session.set_data(f"pref_{key}", value)

            def get_user_preference(session: SessionData, key: str) -> Any:
                return session.get_data(f"pref_{key}", default=None)

        Session validation::

            def is_session_valid(session: SessionData) -> bool:
                return session.is_valid and session.is_active
    """

    id: uuid.UUID
    user_id: uuid.UUID
    session_id: str
    expires_at: datetime
    is_active: bool

    # Session data
    data: dict[str, Any]
    csrf_token: Optional[str]

    # Metadata
    ip_address: Optional[str]
    user_agent: Optional[str]
    last_activity_at: datetime

    @property
    def is_valid(self) -> bool:
        """Check if session is valid.

        Returns:
            bool: True if session is valid and not expired
        """
        ...

    def set_data(self, key: str, value: Any) -> None:
        """Set session data.

        Args:
            key (str): Data key
            value (Any): Data value
        """
        ...

    def get_data(self, key: str, default: Any = None) -> Any:
        """Get session data.

        Args:
            key (str): Data key
            default (Any): Default value if key not found

        Returns:
            Any: Session data value or default
        """
        ...


class OrbitalTokenData(Protocol):
    """One-time token interface (orbital token).

    Used for email verification, password reset, and other
    single-use authentication workflows.

    Attributes:
        id (uuid.UUID): Token identifier
        user_id (uuid.UUID): Associated user ID
        token_hash (str): Hashed token value
        token_type (str): Type of token
        purpose (str): Token purpose description
        expires_at (datetime): Token expiration
        is_used (bool): Whether token has been consumed
        token_metadata (dict[str, Any]): Additional token data
        ip_address (Optional[str]): Creation IP address
        used_at (Optional[datetime]): Usage timestamp

    Example:
        Email verification token::

            def create_verification_token(user_id: uuid.UUID) -> OrbitalTokenData:
                token = EmailVerificationToken(
                    user_id=user_id,
                    token_type="email_verification",
                    purpose="Verify email address",
                    expires_at=datetime.utcnow() + timedelta(hours=24)
                )
                return token

        Token consumption::

            def verify_email_with_token(token: OrbitalTokenData) -> bool:
                if not token.is_valid:
                    return False
                token.consume()
                return True
    """

    id: uuid.UUID
    user_id: uuid.UUID
    token_hash: str
    token_type: str
    purpose: str
    expires_at: datetime
    is_used: bool

    # Metadata
    token_metadata: dict[str, Any]
    ip_address: Optional[str]
    used_at: Optional[datetime]

    @property
    def is_valid(self) -> bool:
        """Check if token is valid.

        Returns:
            bool: True if token is valid, not used, and not expired
        """
        ...

    def consume(self) -> None:
        """Mark token as used."""
        ...

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get token metadata.

        Args:
            key (str): Metadata key
            default (Any): Default value if key not found

        Returns:
            Any: Metadata value or default
        """
        ...


class AuthenticationResult(Protocol):
    """Authentication result interface.

    Contains information about login attempt results including
    tokens, session data, and authentication status.

    Attributes:
        user_id (uuid.UUID): Authenticated user ID
        access_token (str): JWT access token
        refresh_token (Optional[str]): Refresh token
        token_type (str): Token type (usually "bearer")
        expires_in (int): Token expiration in seconds
        csrf_token (Optional[str]): CSRF protection token
        requires_verification (bool): Whether additional verification needed
        session_id (Optional[str]): Session identifier
        is_successful (bool): Whether authentication succeeded
        failure_reason (Optional[str]): Reason for failure if unsuccessful

    Example:
        Successful authentication::

            def process_login_result(result: AuthenticationResult):
                if result.is_successful:
                    set_auth_cookies(result.access_token, result.refresh_token)
                    if result.requires_verification:
                        redirect_to_2fa_page()
                    else:
                        redirect_to_dashboard()
                else:
                    show_error(result.failure_reason)
    """

    user_id: uuid.UUID
    access_token: str
    refresh_token: Optional[str]
    token_type: str
    expires_in: int

    # Additional data
    csrf_token: Optional[str]
    requires_verification: bool
    session_id: Optional[str]

    # Authentication status
    is_successful: bool
    failure_reason: Optional[str]


class AuthenticationAttempt(Protocol):
    """Authentication attempt interface.

    Used for logging and security analysis of login attempts.

    Attributes:
        user_id (Optional[uuid.UUID]): User ID if known
        email_or_username (str): Login identifier used
        is_successful (bool): Whether attempt succeeded
        failure_reason (Optional[str]): Reason for failure
        ip_address (Optional[str]): Client IP address
        user_agent (Optional[str]): Client user agent
        timestamp (datetime): Attempt timestamp
        device_fingerprint (Optional[str]): Device fingerprint
        is_suspicious (bool): Whether attempt appears suspicious
        blocked_until (Optional[datetime]): Blocking end time

    Example:
        Logging authentication attempts::

            def log_auth_attempt(attempt: AuthenticationAttempt):
                if attempt.is_suspicious:
                    await security_alert(f"Suspicious login: {attempt.email_or_username}")

                if attempt.is_successful:
                    await audit_log("successful_login", attempt.user_id)
                else:
                    await rate_limit_check(attempt.ip_address)
    """

    user_id: Optional[uuid.UUID]
    email_or_username: str
    is_successful: bool
    failure_reason: Optional[str]

    # Metadata
    ip_address: Optional[str]
    user_agent: Optional[str]
    timestamp: datetime
    device_fingerprint: Optional[str]

    # Security flags
    is_suspicious: bool
    blocked_until: Optional[datetime]


class PasswordResetRequest(Protocol):
    """Password reset request interface.

    Manages password reset workflow with secure token handling.

    Attributes:
        user_id (uuid.UUID): User requesting reset
        email (str): User's email address
        token (str): Reset token
        expires_at (datetime): Token expiration
        is_used (bool): Whether token has been used
        ip_address (Optional[str]): Request IP address
        requested_at (datetime): Request timestamp
        used_at (Optional[datetime]): Usage timestamp

    Example:
        Password reset workflow::

            def initiate_password_reset(email: str) -> PasswordResetRequest:
                user = get_user_by_email(email)
                request = create_reset_request(user.id, email)
                send_reset_email(email, request.token)
                return request

            def complete_password_reset(request: PasswordResetRequest, new_password: str) -> bool:
                if not request.is_valid:
                    return False
                update_user_password(request.user_id, new_password)
                return True
    """

    user_id: uuid.UUID
    email: str
    token: str
    expires_at: datetime
    is_used: bool

    # Metadata
    ip_address: Optional[str]
    requested_at: datetime
    used_at: Optional[datetime]

    @property
    def is_valid(self) -> bool:
        """Check if reset request is valid.

        Returns:
            bool: True if request is valid and not expired
        """
        ...


class EmailVerificationRequest(Protocol):
    """Email verification request interface.

    Manages email verification workflow.

    Attributes:
        user_id (uuid.UUID): User to verify
        email (str): Email address to verify
        token (str): Verification token
        expires_at (datetime): Token expiration
        is_verified (bool): Whether email is verified
        requested_at (datetime): Request timestamp
        verified_at (Optional[datetime]): Verification timestamp

    Example:
        Email verification workflow::

            def send_verification_email(user_id: uuid.UUID, email: str):
                request = create_verification_request(user_id, email)
                send_verification_email(email, request.token)

            def verify_email(request: EmailVerificationRequest) -> bool:
                if not request.is_valid:
                    return False
                mark_email_verified(request.user_id)
                return True
    """

    user_id: uuid.UUID
    email: str
    token: str
    expires_at: datetime
    is_verified: bool

    # Metadata
    requested_at: datetime
    verified_at: Optional[datetime]

    @property
    def is_valid(self) -> bool:
        """Check if verification request is valid.

        Returns:
            bool: True if request is valid and not expired
        """
        ...


class SecurityEvent(Protocol):
    """Security event interface.

    Used for security auditing and monitoring with structured
    event data and severity levels.

    Attributes:
        user_id (Optional[IdType]): Associated user ID
        event_type (StrType): Type of security event
        event_data (dict[str, Any]): Event-specific data
        severity (EventSeverityType): Event severity level
        ip_address (Optional[StrType]): Client IP address
        user_agent (Optional[StrType]): Client user agent
        timestamp (DateType): Event timestamp
        session_id (Optional[StrType]): Associated session
        request_id (Optional[StrType]): Request identifier

    Example:
        Security event logging::

            def log_failed_login(user_id: uuid.UUID, ip: str):
                event = SecurityEvent(
                    user_id=user_id,
                    event_type="failed_login",
                    severity="medium",
                    ip_address=ip,
                    event_data={"attempts": 3}
                )
                await security_logger.log(event)

        Event anonymization::

            def export_security_logs():
                events = get_security_events()
                anonymized = [event.anonymize() for event in events]
                return anonymized
    """

    user_id: Optional[IdType]
    event_type: StrType
    event_data: dict[str, Any]
    severity: EventSeverityType  # low, medium, high, critical

    # Metadata
    ip_address: Optional[StrType]
    user_agent: Optional[StrType]
    timestamp: DateType

    # Context
    session_id: Optional[StrType]
    request_id: Optional[StrType]

    def anonymize(self) -> "SecurityEvent":
        """Anonymize sensitive data.

        Returns:
            SecurityEvent: Event with anonymized sensitive information
        """
        ...


class TwoFactorAuth(Protocol):
    """Two-factor authentication interface.

    Supports multiple 2FA methods including TOTP, SMS, and email.

    Attributes:
        user_id (IdType): Associated user ID
        method (TwoFAMethodType): 2FA method (totp, sms, email)
        secret (Optional[StrType]): Secret key for TOTP
        backup_codes (list[str]): Emergency backup codes
        is_enabled (BoolType): Whether 2FA is enabled
        enabled_at (Optional[DateType]): Enablement timestamp
        last_used_at (Optional[DateType]): Last usage timestamp

    Example:
        TOTP setup::

            def setup_totp(user_id: uuid.UUID) -> TwoFactorAuth:
                totp = create_totp_2fa(user_id)
                qr_code = generate_qr_code(totp.secret)
                return totp

        2FA verification::

            def verify_2fa_code(two_fa: TwoFactorAuth, code: str) -> bool:
                if two_fa.method == "totp":
                    return two_fa.verify_code(code)
                elif two_fa.method == "sms":
                    return verify_sms_code(two_fa.user_id, code)
                return False
    """

    user_id: IdType
    method: TwoFAMethodType  # totp, sms, email
    secret: Optional[StrType]
    backup_codes: list[str]
    is_enabled: BoolType

    # Metadata
    enabled_at: Optional[DateType]
    last_used_at: Optional[DateType]

    def generate_code(self) -> str:
        """Generate authentication code.

        Returns:
            str: Generated authentication code
        """
        ...

    def verify_code(self, code: str) -> bool:
        """Verify authentication code.

        Args:
            code (str): Code to verify

        Returns:
            bool: True if code is valid
        """
        ...


# Type aliases for convenience
TokenData = TokenPayload
RefreshToken = RefreshTokenData
Session = SessionData
OrbitalToken = OrbitalTokenData
AuthResult = AuthenticationResult
AuthAttempt = AuthenticationAttempt
SecurityLog = SecurityEvent
TwoFA = TwoFactorAuth

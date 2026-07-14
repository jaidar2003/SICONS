class AuthApplicationError(Exception):
    """Base error for authentication and user-management use cases."""


class InvalidAuthRequest(AuthApplicationError):
    """The request violates an authentication or account rule."""


class InvalidCredentials(AuthApplicationError):
    """The supplied credentials cannot authenticate an active user."""


class AuthResourceNotFound(AuthApplicationError):
    """The requested user or recovery identity does not exist."""


class AuthConflict(AuthApplicationError):
    """A unique account identity is already registered."""

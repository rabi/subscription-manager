from typing import Optional

from dasbus.error import DBusError


class RHSMDBusError(DBusError):
    """Parent class for all our exceptions."""

    pass


class ValidationFailed(RHSMDBusError):
    """Input is not valid."""

    def __init__(self, message: Optional[str] = None):
        super().__init__(message or "Validation failed.")


class MissingPermissionsError(RHSMDBusError):
    """The action requires root permission."""

    def __init__(self, message: Optional[str] = None):
        super().__init__(message or "This call requires root permisisons.")


class SystemNotRegisteredError(RHSMDBusError):
    """The action requires the system to be registered."""

    def __init__(self, message: Optional[str] = None):
        super().__init__(message or "This action requires the system to be registered.")


class SystemRegisteredError(RHSMDBusError):
    """The action requires the system not to be registered."""

    def __init__(self, message: Optional[str] = None):
        super().__init__(message or "This action requires the system not to be registered.")


class SystemNotInSCAModeError(RHSMDBusError):
    """System must be in Simple Content Access mode."""

    def __init__(self, message: Optional[str] = None):
        super().__init__(
            message or "This action requires the system to be in Simple Content Access mode."
        )


class SystemInSCAModeError(RHSMDBusError):
    """System can't be in Simple Content Access mode."""

    def __init__(self, message: Optional[str] = None):
        super().__init__(
            message or "This action requires the system not to be in Simple Content Access mode."
        )


class OrganizationNotSpecified(RHSMDBusError):
    def __init__(self, username: str):
        self.username = username

    def __str__(self) -> str:
        return (
            f"User {self.username} is member of more organizations, "
            "but no organization was selected."
        )

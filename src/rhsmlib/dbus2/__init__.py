from dasbus.connection import SessionMessageBus
from dasbus.connection import SystemMessageBus  # noqa: F401
from dasbus.server.interface import DBusSpecificationGenerator

# Define the message bus.
SESSION_BUS = SessionMessageBus()
# We're not authorized to send system messages in development setup
# SESSION_BUS = SystemMessageBus()

NAMESPACE = ("com", "redhat", "RHSM2")

# Dasbus does not support own-specification of methods that are also available
# at default interface org.freedesktop.DBus.Properties, mainly Get() and Set().
# This alters an internal check that is too strict -- two different interfaces
# CAN have the same method names.
# See https://github.com/rhinstaller/dasbus/issues/79.
DBusSpecificationGenerator._is_defined = lambda *args, **kwargs: False

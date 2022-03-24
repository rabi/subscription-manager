import logging
import json

from dasbus.identifier import DBusServiceIdentifier
from dasbus.server.interface import dbus_interface, dbus_signal
from dasbus.server.template import BasicInterfaceTemplate
from dasbus.signal import Signal
from dasbus.typing import Str

from rhsmlib.services.consumer import Consumer as ConsumerService
from rhsmlib.dbus2 import NAMESPACE, SESSION_BUS
from rhsmlib.dbus2.objects import ImplementationBase
from rhsmlib.dbus2.errors import RHSMDBusError

import subscription_manager.utils
from subscription_manager.i18n import Locale


log = logging.getLogger(__name__)


CONSUMER_IDENTIFIER = DBusServiceIdentifier(
    namespace=NAMESPACE + ("Consumer",),
    message_bus=SESSION_BUS,
)


@dbus_interface(CONSUMER_IDENTIFIER.interface_name)
class ConsumerInterface(BasicInterfaceTemplate):
    """The interface to get information about current consumer."""

    # Signals

    def connect_signals(self):
        self.implementation.changed.connect(self.ConsumerChanged)

    @dbus_signal
    def ConsumerChanged(self):
        """Activated when consumer is created, changed or deleted."""
        log.debug("D-Bus signal from {source} emitted.".format(source=type(self).__name__))
        return None

    # Methods

    def GetUuid(
        self,
        locale: Str,
    ) -> Str:
        return self.implementation.get_uuid(locale)

    def GetOrg(
        self,
        locale: Str,
    ) -> Str:
        return self.implementation.get_org(locale)


class ConsumerObject(ImplementationBase):

    # Signals

    def __init__(self):
        self._changed = Signal()

    @property
    def changed(self):
        return self._changed

    # Publication

    def for_publication(self):
        return ConsumerInterface(self)

    # Methods

    def get_uuid(self, locale: Str) -> Str:
        Locale.set(locale)

        service = ConsumerService()
        try:
            uuid: Str = service.get_consumer_uuid()
        except Exception as exc:
            raise RHSMDBusError(str(exc))

        return uuid

    def get_org(self, locale: Str) -> Str:
        Locale.set(locale)

        org: dict = subscription_manager.utils.get_current_owner()
        return json.dumps(org)

import logging

from dasbus.identifier import DBusServiceIdentifier
from dasbus.server.interface import dbus_interface
from dasbus.server.template import BasicInterfaceTemplate
from dasbus.typing import Dict, Str, Variant

from rhsm.connection import UEPConnection

from rhsmlib.services.unregister import UnregisterService
from rhsmlib.dbus2 import NAMESPACE, SESSION_BUS
from rhsmlib.dbus2.objects import ImplementationBase
from rhsmlib.dbus2.errors import RHSMDBusError

import subscription_manager.utils
from subscription_manager.i18n import Locale


log = logging.getLogger(__name__)


UNREGISTER_IDENTIFIER = DBusServiceIdentifier(
    namespace=NAMESPACE + ("Unregister",),
    message_bus=SESSION_BUS,
)


@dbus_interface(UNREGISTER_IDENTIFIER.interface_name)
class UnregisterInterface(BasicInterfaceTemplate):
    """The interface for attaching subscriptions."""

    # Signals: None

    # Methods

    def Unregister(
        self,
        proxy_options: Dict[Str, Variant],
        locale: Str,
    ) -> None:
        return self.implementation.unregister(proxy_options, locale)


class UnregisterObject(ImplementationBase):

    # Signals: None

    # Publication

    def for_publication(self):
        return UnregisterInterface(self)

    # Methods

    def unregister(
        self,
        proxy_options: Dict[Str, Variant],
        locale: Str,
    ) -> None:
        self.ensure_registered()
        Locale.set(locale)

        uep: UEPConnection = self.prepare_connection(proxy_options, proxy_only=True)

        try:
            service = UnregisterService(uep)
            service.unregister()
        except Exception as exc:
            log.exception(exc)
            raise RHSMDBusError(str(exc))

        # The system is now unregistered.
        # Restart virt-who to stop sending host-to-guest mapping.
        subscription_manager.utils.restart_virt_who()

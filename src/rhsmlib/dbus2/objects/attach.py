import logging
import json

from dasbus.identifier import DBusServiceIdentifier
from dasbus.server.interface import dbus_interface
from dasbus.server.template import BasicInterfaceTemplate
from dasbus.typing import Dict, Int32, List, Str, Variant

from rhsm.connection import UEPConnection

from rhsmlib.services.attach import AttachService
from rhsmlib.dbus2 import NAMESPACE, SESSION_BUS
from rhsmlib.dbus2.objects import ImplementationBase
from rhsmlib.dbus2.errors import (
    RHSMDBusError,
    ValidationFailed,
    SystemInSCAModeError,
)

import subscription_manager.utils
from subscription_manager.i18n import Locale


log = logging.getLogger(__name__)


ATTACH_IDENTIFIER = DBusServiceIdentifier(
    namespace=NAMESPACE + ("Attach",),
    message_bus=SESSION_BUS,
)


@dbus_interface(ATTACH_IDENTIFIER.interface_name)
class AttachInterface(BasicInterfaceTemplate):
    """The interface for attaching subscriptions."""

    # Signals: None

    # Methods

    def AutoAttach(
        self,
        service_level: Str,
        options: Dict[Str, Variant],
        locale: Str,
    ) -> Str:
        return self.implementation.auto_attach(service_level, options, locale)

    def PoolAttach(
        self,
        pools: List[Str],
        quantity: Int32,
        options: Dict[Str, Variant],
        locale: Str,
    ) -> List[Str]:
        return self.implementation.pool_attach(pools, quantity, options, locale)


class AttachObject(ImplementationBase):
    """Implementation for attaching subscriptions.

    Results are JSON string or list of JSON strings.

    We don't return the JSON in actual dictionary because deeply nested
    structures are a nightmare in DBus land.
    See https://stackoverflow.com/questions/31658423/.
    """

    # Signals: None

    # Publication

    def for_publication(self):
        return AttachInterface(self)

    # Methods

    def auto_attach(
        self,
        service_level: Str,
        options: Dict[Str, Variant],
        locale: Str,
    ) -> Str:
        self.ensure_registered()
        Locale.set(locale)

        uep: UEPConnection = self.prepare_connection(options, proxy_only=True)

        if subscription_manager.utils.is_simple_content_access(uep=uep):
            raise SystemInSCAModeError()

        service = AttachService(uep)

        try:
            response: dict = service.attach_auto(service_level)
        except Exception as exc:
            log.exception(exc)
            raise RHSMDBusError(str(exc))

        # TODO [migrated] Call only when something got attached
        subscription_manager.entcertlib.EntCertActionInvoker().update()

        return json.dumps(response)

    def pool_attach(
        self,
        pools: List[Str],
        quantity: Int32,
        options: Dict[Str, Variant],
        locale: Str,
    ) -> List[Str]:
        self.ensure_registered()
        Locale.set(locale)

        if quantity < 1:
            raise ValidationFailed("Quantity must be a positive number.")

        uep: UEPConnection = self.prepare_connection(options, proxy_only=True)

        if subscription_manager.utils.is_simple_content_access(uep=uep):
            raise SystemInSCAModeError()

        service = AttachService(uep)

        try:
            result: List = []
            for pool in pools:
                response = service.attach_pool(pool, quantity)
                result.append(json.dumps(response))
        except Exception as exc:
            log.exception(exc)
            raise RHSMDBusError(str(exc))

        # TODO [migrated] Call only when something got attached
        subscription_manager.entcertlib.EntCertActionInvoker().update()

        return result

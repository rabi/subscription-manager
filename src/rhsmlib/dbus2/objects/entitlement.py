import datetime
import logging
import json
from typing import Optional

from dasbus.identifier import DBusServiceIdentifier
from dasbus.server.interface import dbus_interface, dbus_signal
from dasbus.server.template import BasicInterfaceTemplate
from dasbus.signal import Signal
from dasbus.typing import Dict, List, Str, Variant

from rhsm.connection import UEPConnection

from rhsmlib.services.entitlement import EntitlementService
from rhsmlib.dbus2 import NAMESPACE, SESSION_BUS
from rhsmlib.dbus2.objects import ImplementationBase
from rhsmlib.dbus2.errors import RHSMDBusError

from subscription_manager.i18n import Locale


log = logging.getLogger(__name__)


ENTITLEMENT_IDENTIFIER = DBusServiceIdentifier(
    namespace=NAMESPACE + ("Entitlement",),
    message_bus=SESSION_BUS,
)


@dbus_interface(ENTITLEMENT_IDENTIFIER.interface_name)
class EntitlementInterface(BasicInterfaceTemplate):
    """The interface to manage pools."""

    # Signals

    def connect_signals(self):
        self.implementation.changed.connect(self.EntitlementChanged)

    @dbus_signal
    def EntitlementChanged(self):
        """Activated when entitlement is created, changed or removed."""
        log.debug("D-Bus signal from {source} emitted.".format(source=type(self).__name__))
        return None

    # Methods

    def GetStatus(
        self,
        on_date: Str,
        locale: Str,
    ) -> Str:
        return self.implementation.get_status(on_date, locale)

    def GetPools(
        self,
        options: Dict[Str, Variant],
        proxy_options: Dict[Str, Variant],
        locale: Str,
    ) -> Str:
        return self.implementation.get_pools(options, proxy_options, locale)

    def RemoveAllEntitlements(
        self,
        proxy_options: Dict[Str, Variant],
        locale: Str,
    ) -> Str:
        return self.implementation.remove_all(proxy_options, locale)

    def RemoveAllEntitlementsByPoolIds(
        self,
        pool_ids: List[Str],
        proxy_options: Dict[Str, Variant],
        locale: Str,
    ) -> Str:
        return self.implementation.remove_all_by_pool_ids(pool_ids, proxy_options, locale)

    def RemoveAllEntitlementsBySerials(
        self,
        serials: List[Str],
        proxy_options: Dict[Str, Variant],
        locale: Str,
    ) -> Str:
        return self.implementation.remove_all_by_serials(serials, proxy_options, locale)


class EntitlementObject(ImplementationBase):

    # Signals

    def __init__(self):
        self._changed = Signal()

    @property
    def changed(self):
        return self._changed

    # Publication

    def for_publication(self):
        return EntitlementInterface(self)

    # Internal methods

    @classmethod
    def reload(cls):
        service = EntitlementService()
        # TODO: find better solution
        service.identity.reload()
        service.reload()

    @classmethod
    def _parse_date(cls, date_string: Str) -> datetime.datetime:
        """Return new datetime parsed from date."""
        try:
            date = EntitlementService.parse_date(date_string)
        except ValueError as exc:
            raise RHSMDBusError(str(exc))

        return date

    # Methods

    def get_status(self, on_date: Str, locale: Str) -> Str:
        Locale.set(locale)

        date: Optional[datetime.datetime]
        if on_date == "":
            date = None
        else:
            date = self._parse_date(date)

        options = {}
        uep: UEPConnection = self.prepare_connection(options=options)
        service = EntitlementService(uep)

        try:
            status = service.get_status(on_date=date, force=True)
        except Exception as exc:
            log.exception(exc)
            raise RHSMDBusError(str(exc))

        return json.dumps(status)

    def get_pools(
        self, options: Dict[Str, Variant], proxy_options: Dict[Str, Variant], locale: Str
    ) -> Str:
        Locale.set(locale)

        on_date: str = options.setdefault("on_date", "")
        if on_date != "":
            options["on_date"] = self._parse_date(on_date)

        after_date: str = options.setdefault("after_date", "")
        if after_date != "":
            options["after_date"] = self._parse_date(after_date)

        future: str = options.setdefault("future", "")
        if future != "":
            options["future"] = future

        uep: UEPConnection = self.prepare_connection(proxy_options, proxy_only=True)
        service = EntitlementService(uep)

        pools = service.get_pools(**options)

        return json.dumps(pools)

    def remove_all(
        self,
        proxy_options: Dict[Str, Variant],
        locale: Str,
    ) -> Str:
        Locale.set(locale)

        uep: UEPConnection = self.prepare_connection(proxy_options, proxy_only=True)
        service = EntitlementService(uep)

        result = service.remove_all_entitlements()

        return json.dumps(result)

    def remove_all_by_pool_ids(
        self,
        pool_ids: List[Str],
        proxy_options: Dict[Str, Variant],
        locale: Str,
    ) -> Str:
        Locale.set(locale)

        uep: UEPConnection = self.prepare_connection(proxy_options, proxy_only=True)
        service = EntitlementService(uep)

        _, _, removed_serials = service.remove_entilements_by_pool_ids(pool_ids)

        return json.dumps(removed_serials)

    def remove_all_by_serials(
        self,
        serials: List[Str],
        proxy_options: Dict[Str, Variant],
        locale: Str,
    ) -> Str:
        Locale.set(locale)

        uep: UEPConnection = self.prepare_connection(proxy_options, proxy_only=True)
        service = EntitlementService(uep)

        removed_serials, _ = service.remove_entitlements_by_serials(serials)

        return json.dumps(removed_serials)

import logging
import json

from dasbus.identifier import DBusServiceIdentifier
from dasbus.server.interface import dbus_interface, dbus_signal
from dasbus.server.template import BasicInterfaceTemplate
from dasbus.signal import Signal
from dasbus.typing import Dict, Str

from rhsm.connection import UEPConnection

from syspurpose.files import SyspurposeStore

from rhsmlib.services.syspurpose import Syspurpose as SyspurposeService
from rhsmlib.dbus2 import NAMESPACE, SESSION_BUS
from rhsmlib.dbus2.objects import ImplementationBase
from rhsmlib.dbus2.errors import RHSMDBusError, SystemNotRegisteredError

from subscription_manager.i18n import Locale


log = logging.getLogger(__name__)


SYSPURPOSE_IDENTIFIER = DBusServiceIdentifier(
    namespace=NAMESPACE + ("Syspurpose",),
    message_bus=SESSION_BUS,
)


@dbus_interface(SYSPURPOSE_IDENTIFIER.interface_name)
class SyspurposeInterface(BasicInterfaceTemplate):
    """The interface for managing system purpose."""

    # Signals

    def connect_signals(self):
        self.implementation.changed.connect(self.SyspurposeChanged)

    @dbus_signal
    def SyspurposeChanged(self):
        """Activated when system purpose is created, changed or deleted."""
        log.debug("D-Bus signal from {source} emitted.".format(source=type(self).__name__))
        return None

    # Methods

    def GetSyspurpose(
        self,
        locale: Str,
    ) -> Str:
        return self.implementation.get_syspurpose(locale)

    def GetSyspurposeStatus(
        self,
        locale: Str,
    ) -> Str:
        return self.implementation.get_syspurpose_status(locale)

    def GetValidFields(
        self,
        locale: Str,
    ) -> Str:
        return self.implementation.get_valid_fields(locale)

    def SetSyspurpose(
        self,
        values: Dict[Str, Str],
        locale: Str,
    ) -> Str:
        return self.implementation.set_syspurpose(values, locale)


class SyspurposeObject(ImplementationBase):
    syspurpose_path: str = "/etc/rhsm/syspurpose/syspurpose.json"

    # Signals

    def __init__(self):
        self._changed = Signal()

    @property
    def changed(self):
        return self._changed

    # Publication

    def for_publication(self):
        return SyspurposeInterface(self)

    # Methods

    def get_syspurpose(
        self,
        locale: Str,
    ) -> Str:
        Locale.set(locale)

        syspurpose_store = SyspurposeStore.read(self.syspurpose_path)

        try:
            contents = syspurpose_store.contents
        except Exception as exc:
            log.exception(exc)
            raise RHSMDBusError(str(exc))

        return json.dumps(contents)

    def get_syspurpose_status(self, locale: Str) -> Str:
        Locale.set(locale)

        options = {}
        uep: UEPConnection = self.prepare_connection(options)

        service = SyspurposeService(uep)
        syspurpose_status = service.get_syspurpose_status()["status"]
        return service.get_overall_status(syspurpose_status)

    def get_valid_fields(self, locale: Str) -> Str:
        if not self.registered:
            raise SystemNotRegisteredError()

        Locale.set(locale)

        options = {}
        uep: UEPConnection = self.prepare_connection(options)

        service = SyspurposeService(uep)

        valid_fields = service.get_owner_syspurpose_valid_fields()
        if valid_fields is None:
            raise RHSMDBusError("Unable to get valid system purpose fields.")

        return json.dumps(valid_fields)

    def set_syspurpose(self, values: Dict[Str, Str], locale: Str) -> Str:
        Locale.set(locale)

        options = {}
        uep: UEPConnection = self.prepare_connection(options)

        service = SyspurposeService(uep)
        new_values = service.set_syspurpose_values(values)

        # Check if there was any conflict during three-way merge
        conflicts = {}
        for key, value in new_values.items():
            if key in values and values[key] != value:
                conflicts[key] = value
        if conflicts:
            items: str = ", ".join(f"{k} of {v}" for k, v in conflicts.items())
            raise RHSMDBusError(
                "Warning: The following field was recently set for this system "
                "by the entitlement server administrator: " + items
            )

        self.syspurpose_updated.emit()
        return json.dumps(new_values)

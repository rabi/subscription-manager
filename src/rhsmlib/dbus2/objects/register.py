import logging
import json

from dasbus.identifier import DBusServiceIdentifier
from dasbus.server.interface import dbus_interface
from dasbus.server.template import BasicInterfaceTemplate
from dasbus.typing import Dict, Str, Variant

from rhsm.connection import UEPConnection

from rhsmlib.services.register import RegisterService
from rhsmlib.dbus2 import NAMESPACE, SESSION_BUS
from rhsmlib.dbus2.objects import ImplementationBase
from rhsmlib.dbus2.errors import SystemRegisteredError, OrganizationNotSpecified

from subscription_manager.i18n import Locale


log = logging.getLogger(__name__)


REGISTER_IDENTIFIER = DBusServiceIdentifier(
    namespace=NAMESPACE + ("Register",),
    message_bus=SESSION_BUS,
)


@dbus_interface(REGISTER_IDENTIFIER.interface_name)
class RegisterInterface(BasicInterfaceTemplate):
    """The interface for attaching subscriptions."""

    def Register(
        self,
    ) -> None:
        return self.implementation.register()

    def RegisterWithActivationKeys(
        self,
    ) -> None:
        return self.implementation.register_with_activation_keys()


class RegisterObject(ImplementationBase):
    def __init__(self):
        self._get_owner_cb = None
        self._no_owner_cb = None

    def register(
        self,
        org: Str,
        username: Str,
        password: Str,
        options: Dict[Str, Variant],
        connection_options: Dict[Str, Variant],
        locale: Str,
    ) -> None:
        if self.registered:
            raise SystemRegisteredError()

        Locale.set(locale)

        connection_options["username"] = username
        connection_options["password"] = password

        uep: UEPConnection = self.prepare_connection(connection_options)

        service = RegisterService(uep)

        # Try to get organization from the list of available orgainzations.
        # If the list contains only one item, the function returns it.
        if not org:
            org = service.determine_owner_key(
                username=username,
                get_owner_cb=self._get_owner_cb,
                no_owner_cb=self._no_owner_cb,
            )

        # If there are multiple organizations, the signal was triggered in
        # callback method _get_owner_cb. Some exception has to be raised here
        # to prevent the registration process.
        if not org:
            raise OrganizationNotSpecified(username=username)

        # Remove enable_content option, because it is not needed for
        # registration
        enable_content = self._remove_enable_content_option(options)
        # FIXME ^^ This is ugly, you don'd do pop like that

        consumer = service.register(org, **options)

        if enable_content:
            self._enable_content(uep, consumer)

        return json.dumps(consumer)

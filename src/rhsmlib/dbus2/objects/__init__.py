import os

from dasbus.typing import Dict, Str, Variant
from dasbus.server.publishable import Publishable

import rhsm.config
from rhsm.connection import UEPConnection
from subscription_manager.cp_provider import CPProvider
from subscription_manager.identity import Identity
import rhsmlib.services.config

import subscription_manager.utils
from subscription_manager import injection as inj
from subscription_manager.injectioninit import init_dep_injection


from rhsmlib.dbus2.errors import (
    MissingPermissionsError,
    SystemNotRegisteredError,
    ValidationFailed,
)

init_dep_injection()


class ImplementationBase(Publishable):
    """Abstract interface providing some basic methods to child objects."""

    @property
    def root(self) -> bool:
        return os.getuid() == 0

    def ensure_root(self):
        """Raise exception if the program is not run as root."""
        if not self.root:
            raise MissingPermissionsError()

    @property
    def registered(self) -> bool:
        identity: Identity = inj.require(inj.IDENTITY)
        return identity.is_valid()

    def ensure_registered(self):
        """Raise exception if the system is not registered."""
        self.ensure_root()

        if not self.registered:
            raise SystemNotRegisteredError()

    def _validate_only_proxy_options(self, options: Dict[Str, Variant]) -> None:
        """Check that all options are proxy related."""
        for key in options.keys():
            if key not in (
                "proxy_hostname",
                "proxy_port",
                "proxy_user",
                "proxy_password",
                "no_proxy",
            ):
                raise ValidationFailed(f"{key} is not a valid proxy option.")

    def prepare_connection(
        self,
        options: Dict[Str, Variant],
        proxy_only: bool = False,
        basic_auth_method: bool = False,
    ) -> UEPConnection:
        """Build connection to Red Hat Unified Entitlement Platform."""
        system_config = rhsmlib.services.config.Config(rhsm.config.get_config_parser())
        server_config = system_config["server"]

        server_provider: CPProvider = inj.require(inj.CP_PROVIDER)
        if proxy_only:
            self._validate_only_proxy_options(options)

        connection_info = {
            # server
            "host": options.get("host", server_config["hostname"]),
            "ssl_port": options.get("port", server_config.get_int("port")),
            "handler": options.get("handler", server_config["prefix"]),
            # proxy
            "proxy_hostname_arg": options.get("proxy_hostname", server_config["proxy_hostname"]),
            "proxy_port_arg": options.get("proxy_port", server_config.get_int("proxy_port")),
            "proxy_user_arg": options.get("proxy_user", server_config["proxy_user"]),
            "proxy_password_arg": options.get("proxy_password", server_config["proxy_password"]),
            "no_proxy_arg": options.get("no_proxy", server_config["no_proxy"]),
        }

        server_provider.set_connection_info(**connection_info)
        server_provider.set_correlation_id(subscription_manager.utils.generate_correlation_id())

        if self.registered and basic_auth_method is False:
            return server_provider.get_consumer_auth_cp()
        if "username" in options and "password" in options:
            server_provider.set_user_pass(options["username"], options["password"])
            return server_provider.get_basic_auth_cp()
        return server_provider.get_no_auth_cp()

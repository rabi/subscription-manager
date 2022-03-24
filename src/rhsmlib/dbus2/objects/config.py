import logging
import json
from iniparse import ini

from dasbus.identifier import DBusServiceIdentifier
from dasbus.server.interface import dbus_interface, dbus_signal
from dasbus.server.template import BasicInterfaceTemplate
from dasbus.signal import Signal
from dasbus.typing import Dict, Str, Variant

import rhsm.config
import rhsmlib.services.config
from rhsmlib.dbus2 import NAMESPACE, SESSION_BUS
from rhsmlib.dbus2.objects import ImplementationBase
from rhsmlib.dbus2.errors import RHSMDBusError

from subscription_manager.i18n import Locale


log = logging.getLogger(__name__)


CONFIG_IDENTIFIER = DBusServiceIdentifier(
    namespace=NAMESPACE + ("Config",),
    message_bus=SESSION_BUS,
)


@dbus_interface(CONFIG_IDENTIFIER.interface_name)
class ConfigInterface(BasicInterfaceTemplate):
    """The interface for managing RHSM configuration."""

    # Signals

    def connect_signals(self):
        self.implementation.changed.connect(self.ConfigChanged)

    @dbus_signal
    def ConfigChanged(self):
        log.debug("D-Bus signal from {source} emitted.".format(source=type(self).__name__))
        return None

    # Methods

    def Get(
        self,
        property_name: Str,
        locale: Str,
    ) -> Str:
        return self.implementation.get(property_name, locale)

    def GetSection(self, section_name: Str, locale: Str) -> Str:
        return self.implementation.get_section(section_name, locale)

    def GetAll(self, locale: Str) -> Str:
        """Get whole configuration."""
        return self.implementation.get_all(locale)

    def Set(
        self,
        property_name: Str,
        new_value: Variant,
        locale: Str,
    ) -> None:
        return self.implementation.set(property_name, new_value, locale)

    def SetAll(
        self,
        configuration: Dict[Str, Variant],
        locale: Str,
    ) -> None:
        return self.implementation.set_all(configuration, locale)


class ConfigObject(ImplementationBase):

    # Signals

    def __init__(self):
        super().__init__()
        self.config = rhsmlib.services.config.Config(rhsm.config.get_config_parser())
        self._changed = Signal()

    @property
    def changed(self):
        return self._changed

    # Publication

    def for_publication(self):
        return ConfigInterface(self)

    # Internal methods

    def _reload(self):
        """Update in-memory config when i-notify or periodical polling
        detects any change of rhsm.conf file."""
        parser = rhsm.config.get_config_parser()

        # Read the configuration file again.
        # Clean all data in parser object, as iniparse doe not provide
        # better method to do that.
        parser.data = ini.INIConfig(None, optionxformsource=parser)
        files_read = parser.read()

        if len(files_read) > 0:
            log.debug(f"File read: {files_read}")
            self.config = rhsm.services.config.Config(parser)
            rhsm.logutil.init_logger(parser)
            log.debug(f"Configuration file {parser.config_file} reloaded: {self.config}.")
            self._changed.emit()
        else:
            log.warning(f"Unable to read configuration file {parser.config_file}.")

    # Methods

    def get(self, full_key: Str, locale: Str) -> Str:
        Locale.set(locale)

        section, _, key = full_key.partition(".")
        if section == "" or key == "":
            raise RHSMDBusError("You have to specify both the section and the property.")

        if section not in self.config.keys():
            raise RHSMDBusError("Specified section is not valid.")
        if key not in self.config[section]:
            raise RHSMDBusError(f"Specified property is not valid for section '{section}'.")

        return self.config[section][key]

    def get_section(self, section: Str, locale: Str) -> Str:
        Locale.set(locale)

        if section not in self.config.keys():
            raise RHSMDBusError("Specified section is not valid.")

        section_data: Dict = {k: v for k, v in self.config[section].items()}
        return json.dumps(section_data)

    def get_all(self, locale: str) -> Str:
        Locale.set(locale)
        d = {}
        for category, content in self.config.items():
            section: Dict = {k: v for k, v in content.items()}
            d[category] = section
        return json.dumps(d)

    def set(self, full_key: Str, new_value: Variant, locale: Str) -> None:
        Locale.set(locale)

        section, _, key = full_key.partition(".")
        if not key:
            raise RHSMDBusError("You have to specify both the section and the property.")

        self.config[section][key] = new_value

        logging_changed: bool = False
        if section == "logging":
            logging_changed = True

        # TODO Resolve this. Wouldn't it be easier if we just loaded the config
        # from file when we need it?
        # Disable directory watcher temporarily.
        # 'self.config.persist()' writes configuration file and it would trigger
        # system monitor callback functoin and saved values would be read again.
        # It can cause race conditions, when Set() is called multiple times.
        # Server.temporary_disable_dir_watchers({CONFIG_WATCHER})

        self.config.persist()

        # Reinitialize logger if it was changed
        if logging_changed:
            parser = rhsm.config.get_config_parser()
            self.config = rhsmlib.services.config.Config(parser)
            rhsm.logutil.init_logger(parser)

    def set_all(self, configuration: Dict[Str, Variant], locale: Str) -> None:
        Locale.set(locale)

        logging_changed: bool = False
        for full_key, new_value in configuration.items():
            section, _, key = full_key.partition(".")
            if not key:
                raise RHSMDBusError("You have to specify both the section and the property.")

            self.config[section][key] = new_value
            if section == "logging":
                logging_changed = True

        # TODO Resolve this. Wouldn't it be easier if we just loaded the config
        # from file when we need it?
        # Disable directory watcher temporarily.
        # 'self.config.persist()' writes configuration file and it would trigger
        # system monitor callback functoin and saved values would be read again.
        # It can cause race conditions, when Set() is called multiple times.
        # Server.temporary_disable_dir_watchers({CONFIG_WATCHER})

        self.config.persist()

        # Reinitialize logger if it was changed
        if logging_changed:
            parser = rhsm.config.get_config_parser()
            self.config = rhsmlib.services.config.Config(parser)
            rhsm.logutil.init_logger(parser)

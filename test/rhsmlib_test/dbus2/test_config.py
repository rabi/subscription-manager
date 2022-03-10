from typing import Tuple

from rhsm.config import RhsmConfigParser
from rhsmlib.services.config import Config
from rhsmlib.dbus2.objects.config import ConfigObject
from rhsmlib.dbus2.errors import RHSMDBusError

import pytest
from parameterized import parameterized

from test import subman_marker_dbus
from test.rhsmlib_test.dbus2.base import DBusTestCase

TEST_LOCALE: str = "en_US"

TEST_CONFIG_SECTIONS: Tuple[str] = ("foo", "server", "rhsm", "rhsmcertd", "logging")

TEST_CONFIG: str = r"""
[foo]
bar =
quux = baz
bigger_than_32_bit = 21474836470
bigger_than_64_bit = 123456789009876543211234567890

[server]
hostname = server.example.com
prefix = /candlepin
port = 8443
insecure = 1
proxy_hostname =
proxy_port =
proxy_user =
proxy_password =

[rhsm]
ca_cert_dir = /etc/rhsm/ca-test/
baseurl = https://content.example.com
repomd_gpg_url =
repo_ca_cert = %(ca_cert_dir)sredhat-uep-non-default.pem
productCertDir = /etc/pki/product
entitlementCertDir = /etc/pki/entitlement
consumerCertDir = /etc/pki/consumer
report_package_profile = 1
pluginDir = /usr/lib/rhsm-plugins
some_option = %(repo_ca_cert)stest
manage_repos =

[rhsmcertd]
certCheckInterval = 245

[logging]
default_log_level = DEBUG
"""


@subman_marker_dbus
class TestConfigObject(DBusTestCase):
    expected_sections = ("foo", "server", "rhsm", "rhsmcertd", "logging")

    def setUp(self):
        super().setUp()

        self.fid = self.create_temp_file(TEST_CONFIG)
        self.parser = RhsmConfigParser(self.fid.name)
        self.config = Config(self.parser)

        # Instantitate ConfigObject
        self.co = ConfigObject()
        self.co.config = self.config

    @parameterized.expand(
        [
            "foo.bigger_than_64_bit",
            "server.hostname",
            "server.port",
            "rhsmcertd.certCheckInterval",
            "logging.default_log_level",
        ],
    )
    def test_get_(self, full_key: str):
        self.assertTrue(self.co.get(full_key, TEST_LOCALE) is not None)

    @parameterized.expand(
        [
            ("", RHSMDBusError, "You have to specify both the section and the property."),
            (".", RHSMDBusError, "You have to specify both the section and the property."),
            ("server", RHSMDBusError, "You have to specify both the section and the property."),
            ("server.", RHSMDBusError, "You have to specify both the section and the property."),
            ("invalid", RHSMDBusError, "You have to specify both the section and the property."),
            ("invalid.", RHSMDBusError, "You have to specify both the section and the property."),
            (".invalid", RHSMDBusError, "You have to specify both the section and the property."),
            ("invalid.invalid", RHSMDBusError, "Specified section is not valid."),
            ("server.invalid", RHSMDBusError, "Specified property is not valid for section 'server'."),
        ]
    )
    def test_get_error_(self, key: str, exc: Exception, exc_text: str):
        with pytest.raises(exc) as excinfo:
            self.co.get(key, TEST_LOCALE)
        self.assertEqual(str(excinfo.value), exc_text)

    @parameterized.expand(TEST_CONFIG_SECTIONS)
    def test_get_section_(self, section: str):
        self.assertTrue(self.co.get_section(section, TEST_LOCALE) is not None)

    @parameterized.expand(
        [
            ("", RHSMDBusError, "Specified section is not valid."),
            (".", RHSMDBusError, "Specified section is not valid."),
            ("invalid", RHSMDBusError, "Specified section is not valid."),
            ("invalid.", RHSMDBusError, "Specified section is not valid."),
            ("invalid.invalid", RHSMDBusError, "Specified section is not valid."),
        ]
    )
    def test_get_section_error_(self, section: str, exc: Exception, exc_text: str):
        with pytest.raises(exc) as excinfo:
            self.co.get_section(section, TEST_LOCALE)
        self.assertEqual(str(excinfo.value), exc_text)

    @parameterized.expand(TEST_CONFIG_SECTIONS)
    def test_get_all_(self, section: str):
        self.assertIn(section, self.co.get_all(TEST_LOCALE))

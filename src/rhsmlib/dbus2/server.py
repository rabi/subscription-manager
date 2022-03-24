from dasbus.connection import MessageBus
from dasbus.loop import EventLoop
from dasbus.xml import XMLGenerator  # noqa: F401

from rhsmlib.dbus2 import SESSION_BUS, NAMESPACE

from rhsmlib.dbus2.objects.attach import ATTACH_IDENTIFIER, AttachObject
from rhsmlib.dbus2.objects.config import CONFIG_IDENTIFIER, ConfigObject
from rhsmlib.dbus2.objects.consumer import CONSUMER_IDENTIFIER, ConsumerObject
from rhsmlib.dbus2.objects.entitlement import ENTITLEMENT_IDENTIFIER, EntitlementObject
from rhsmlib.dbus2.objects.syspurpose import SYSPURPOSE_IDENTIFIER, SyspurposeObject
from rhsmlib.dbus2.objects.unregister import UNREGISTER_IDENTIFIER, UnregisterObject


def prepare_bus(bus: MessageBus) -> MessageBus:
    """Publish interfaces and register the service on the bus."""
    bus.register_service(".".join(NAMESPACE))

    bus.publish_object(
        ATTACH_IDENTIFIER.object_path,
        AttachObject().for_publication(),
    )
    bus.publish_object(
        CONFIG_IDENTIFIER.object_path,
        ConfigObject().for_publication(),
    )
    bus.publish_object(
        CONSUMER_IDENTIFIER.object_path,
        ConsumerObject().for_publication(),
    )
    bus.publish_object(
        ENTITLEMENT_IDENTIFIER.object_path,
        EntitlementObject().for_publication(),
    )
    bus.publish_object(
        UNREGISTER_IDENTIFIER.object_path,
        UnregisterObject().for_publication(),
    )
    bus.publish_object(
        SYSPURPOSE_IDENTIFIER.object_path,
        SyspurposeObject().for_publication(),
    )

    return bus


if __name__ == "__main__":
    SESSION_BUS = prepare_bus(SESSION_BUS)

    try:
        # Start the event loop.
        print(f"Starting {type(SESSION_BUS).__name__} server {'.'.join(NAMESPACE)}...")
        loop = EventLoop()
        loop.run()
    except KeyboardInterrupt:
        # That carriage return '\r' hides the '^C' printed to the stdout
        # by the terminal.
        print("\rShutting down...")
    finally:
        # Unregister the DBus service and objects.
        SESSION_BUS.disconnect()

import tempfile
import unittest


class DBusTestCase(unittest.TestCase):
    """Class for testing DBus methods in the same process.

    During setUp, this class calls a thread that makes a DBus connection and
    exposes some objects on the bus.
    """

    @classmethod
    def create_temp_file(cls, data: str) -> tempfile._TemporaryFileWrapper:
        fid = tempfile.NamedTemporaryFile(mode="w+", suffix=".tmp")
        fid.write(data)
        fid.seek(0)
        return fid

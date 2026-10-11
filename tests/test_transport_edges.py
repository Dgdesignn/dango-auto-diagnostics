import socket
import threading
import time
import unittest
from unittest.mock import patch

from scanner_outo.communication.tcp import TcpElmTransport
from scanner_outo.communication.serial_transport import SerialElmTransport
from scanner_outo.communication.bluetooth import BluetoothElmTransport
from scanner_outo.communication.base import TransportTimeout, TransportDisconnected


class TransportEdgeTests(unittest.TestCase):
    def server(self, action):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        def run():
            try:
                connection, _ = listener.accept()
                with connection:
                    connection.recv(1024)
                    action(connection)
            finally:
                listener.close()
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        self.addCleanup(lambda: thread.join(2))
        return port

    def test_fragmented_tcp(self):
        def fragmented(connection):
            for part in (b"41 ", b"0C 1A", b" F8\r", b">"):
                connection.sendall(part)
                time.sleep(0.01)
        port = self.server(fragmented)
        with TcpElmTransport(port=port) as transport:
            self.assertEqual(transport.request("010C"), "41 0C 1A F8\r>")

    def test_tcp_timeout_closes_socket(self):
        port = self.server(lambda _: time.sleep(0.2))
        with TcpElmTransport(port=port, timeout_seconds=0.05) as transport:
            with self.assertRaises(TransportTimeout):
                transport.request("010C")
            self.assertIsNone(transport._socket)

    def test_tcp_disconnect(self):
        port = self.server(lambda _: None)
        with TcpElmTransport(port=port) as transport:
            with self.assertRaises(TransportDisconnected):
                transport.request("010C")

    def test_serial_and_bluetooth_substitute(self):
        class FakeSerial:
            def __init__(self):
                self.response = bytearray(b"41 0C 1A F8\r>")
                self.written = b""
                self.closed = False
            @property
            def in_waiting(self):
                return 1
            def write(self, data):
                self.written += data
            def read(self, count):
                result = bytes(self.response[:count])
                del self.response[:count]
                return result
            def close(self):
                self.closed = True
        for cls in (SerialElmTransport, BluetoothElmTransport):
            fake = FakeSerial()
            with patch("scanner_outo.communication.serial_transport.serial.serial_for_url", return_value=fake):
                with cls("COM_TEST") as transport:
                    self.assertEqual(transport.request("010C"), "41 0C 1A F8\r>")
                self.assertEqual(fake.written, b"010C\r")
                self.assertTrue(fake.closed)

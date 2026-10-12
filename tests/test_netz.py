"""Tests für die Netzabfragen in scan.py (ohne echtes Netz).

Hintergrund (12.10.2026): In Netzen ohne funktionierendes IPv6 probierte urllib jede
IPv6-Adresse von api.npmjs.org (12 Stück) bis zum Timeout — zwei Minuten pro Paket.
"""
import importlib.util
import socket
import sys
import unittest
from pathlib import Path
from unittest import mock

SCAN = Path(__file__).resolve().parents[1] / "skills" / "repo-pruefer" / "scripts" / "scan.py"
spec = importlib.util.spec_from_file_location("scan", SCAN)
scan_mod = importlib.util.module_from_spec(spec)
sys.modules["scan"] = scan_mod
spec.loader.exec_module(scan_mod)

V6 = (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("2606:4700::1", 443, 0, 0))
V4 = (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("104.16.0.1", 443))


class FakeSocket:
    versuche: list = []

    def __init__(self, familie, typ, proto):
        self.familie = familie

    def settimeout(self, _t):
        pass

    def connect(self, ziel):
        FakeSocket.versuche.append(ziel[0])
        if self.familie == socket.AF_INET6:
            raise TimeoutError("kein IPv6")

    def close(self):
        pass


class IPv4Zuerst(unittest.TestCase):

    def setUp(self):
        FakeSocket.versuche = []

    def test_ipv4_wird_vor_ipv6_probiert(self):
        with mock.patch.object(scan_mod.socket, "getaddrinfo", return_value=[V6, V6, V4]), \
                mock.patch.object(scan_mod.socket, "socket", FakeSocket):
            scan_mod._verbinde_ipv4_zuerst(("api.npmjs.org", 443), timeout=1)
        self.assertEqual(FakeSocket.versuche, ["104.16.0.1"])

    def test_nur_ipv6_wird_trotzdem_versucht(self):
        with mock.patch.object(scan_mod.socket, "getaddrinfo", return_value=[V6]), \
                mock.patch.object(scan_mod.socket, "socket", FakeSocket):
            with self.assertRaises(OSError):
                scan_mod._verbinde_ipv4_zuerst(("nur-v6.example", 443), timeout=1)
        self.assertEqual(FakeSocket.versuche, ["2606:4700::1"])

    def test_verbindung_nutzt_die_eigene_funktion(self):
        conn = scan_mod._HTTPSIPv4Zuerst("api.npmjs.org", timeout=1)
        self.assertIs(conn._create_connection, scan_mod._verbinde_ipv4_zuerst)


if __name__ == "__main__":
    unittest.main()

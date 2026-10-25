#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""System tests of the control path: minidaq_ctl against minidaq_server (Chapter 19).

The unit tests check the parts (the token store, TLS, the protocol, the service). These tests
check how the two programs put them together, as an operator uses them: the client's exit
status, its token, its certificate check, the server's roles and its shutdown. They close
problem report MDQ-PR-015 for the items ctl and server.
"""
import json
import os
import socket
import ssl
import subprocess
import threading
import unittest

from systest import Ctl, Pki, Server, SystemTest, app, eventually, run_config, write_json


def new_token(name, role):
    """(token, token-file entry) from `minidaq_ctl new-token`."""
    p = subprocess.run([app("minidaq_ctl"), "new-token", name, role], capture_output=True, text=True,
                       check=True)
    token, entry = p.stdout.splitlines()
    return token, json.loads(entry)


def secret_file(path, text):
    path.write_text(text + "\n")
    path.chmod(0o600)
    return path


class ClientAndServer(SystemTest):
    def test_an_operator_runs_an_acquisition_with_the_client(self):
        # REQ: SRS-CTL-040, SRS-CTL-043, SRS-SEC-009
        cfg = write_json(self.tmp / "run.json", run_config(self.tmp, seconds=0.5))
        with Server(self.tmp) as server:
            self.assertIn("token in", server.banner)
            self.assertEqual(server.token_file.stat().st_mode & 0o777, 0o600)
            ctl = Ctl(server)  # finds the start-up token where the server wrote it
            self.assertEqual(ctl.ok("hello")["auth"], "token")
            self.assertEqual(ctl.status()["state"], "idle")
            status = ctl.run(cfg)
            self.assertTrue(status["integrity"]["complete"], status["integrity"])
            self.assertEqual(status["sorter"]["singles_in"], 500_000)
            self.assertEqual(server.stop(), 0, server.output)
        self.assertFalse(server.token_file.exists(), "the start-up token outlived the server")

    def test_the_exit_status_says_who_refused(self):
        # REQ: SRS-CTL-040
        with Server(self.tmp) as server:
            ctl = Ctl(server)
            code, response, _ = ctl("start")  # illegal in idle: the server refuses
            self.assertEqual(code, 1)
            self.assertEqual(response["error"]["code"], "illegal_transition")
            code, _, err = ctl("frobnicate")
            self.assertEqual(code, 1, err)
            self.assertEqual(ctl("configure")[0], 2)  # usage: no file
            self.assertEqual(ctl("configure", str(self.tmp / "missing.json"))[0], 2)
            code, _, err = Ctl(server, token_file=self.tmp / "missing.token")("status")
            self.assertEqual(code, 2, err)
            self.assertIn("token", err)
            port = server.port
        # Nothing listens on the port any more.
        code, _, err = Ctl(server)("status")
        self.assertEqual(code, 2)
        self.assertIn(f"cannot connect to 127.0.0.1:{port}", err)

    def test_new_token_refuses_an_unknown_role(self):
        # REQ: SRS-CTL-040
        p = subprocess.run([app("minidaq_ctl"), "new-token", "alice", "admin"], capture_output=True, text=True,
                           timeout=30)
        self.assertEqual(p.returncode, 2)
        self.assertEqual(p.stdout, "", "no token may be printed for a refused role")

    def test_a_server_without_authentication_needs_no_token(self):
        # REQ: SRS-CTL-040
        with Server(self.tmp, "--no-auth") as server:
            p = subprocess.run([app("minidaq_ctl"), "--port", str(server.port), "status"], capture_output=True,
                               text=True, timeout=30, env=server.env)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(json.loads(p.stdout)["status"]["state"], "idle")

    def test_wait_ends_at_its_deadline(self):
        # REQ: SRS-CTL-042
        with Server(self.tmp) as server:
            code, _, err = Ctl(server)("wait", "running", "0.3")
            self.assertEqual(code, 1)
            self.assertIn("timeout: state is idle", err)

    def test_a_wrong_token_is_refused_and_the_connection_closed(self):
        # REQ: SRS-CTL-040, SRS-SEC-002
        with Server(self.tmp, "--audit", str(self.tmp / "audit.jsonl")) as server:
            wrong = secret_file(self.tmp / "wrong.token", "not-the-token")
            code, response, _ = Ctl(server, token_file=wrong)("status")
            self.assertEqual(code, 1)
            self.assertFalse(response["ok"])
            self.assertEqual(server.stop(), 0)
        audit = (self.tmp / "audit.jsonl").read_text()
        self.assertIn("auth", audit)
        self.assertNotIn("not-the-token", audit)


class Roles(SystemTest):
    def test_an_observer_reads_the_status_and_cannot_start(self):
        # REQ: SRS-SEC-003, SRS-CTL-040
        op_token, op_entry = new_token("alice", "operator")
        ob_token, ob_entry = new_token("bob", "observer")
        tokens = write_json(self.tmp / "tokens.json", {"tokens": [op_entry, ob_entry]})
        tokens.chmod(0o600)
        cfg = write_json(self.tmp / "run.json", run_config(self.tmp, seconds=0.2))
        with Server(self.tmp, "--tokens", str(tokens)) as server:
            self.assertIn("tokens from", server.banner)
            self.assertFalse(server.token_file.exists(), "a server with a token file makes no token")
            observer = Ctl(server, token_file=secret_file(self.tmp / "bob.token", ob_token))
            operator = Ctl(server, token_file=secret_file(self.tmp / "alice.token", op_token))
            self.assertEqual(observer.status()["state"], "idle")
            code, response, _ = observer("configure", str(cfg))
            self.assertEqual(code, 1)
            self.assertEqual(response["error"]["code"], "forbidden")
            self.assertEqual(operator.ok("configure", str(cfg))["state"], "configured")
            self.assertEqual(observer.status()["state"], "configured")


class ImpostorServer:
    """A TLS server that presents a certificate and records whether any application data came."""

    def __init__(self, cert, key):
        self.ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.ctx.minimum_version = ssl.TLSVersion.TLSv1_3
        self.ctx.load_cert_chain(cert, key)
        self.sock = socket.create_server(("127.0.0.1", 0))
        self.port = self.sock.getsockname()[1]
        self.received = b""
        self.handshakes = 0
        self.thread = threading.Thread(target=self._serve, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.sock.close()
        self.thread.join(timeout=5)

    def _serve(self):
        self.sock.settimeout(30)
        try:
            conn, _ = self.sock.accept()
        except OSError:
            return
        with conn:
            conn.settimeout(10)
            try:
                with self.ctx.wrap_socket(conn, server_side=True) as tls:
                    self.handshakes += 1
                    while chunk := tls.recv(4096):
                        self.received += chunk
            except (ssl.SSLError, OSError):
                pass  # the client refused the certificate: the handshake ends here


class Tls(SystemTest):
    def setUp(self):
        super().setUp()
        self.pki = Pki(self.tmp / "pki")
        self.cert, self.key = self.pki.server("minidaq")

    def test_the_client_talks_to_a_server_its_ca_signed(self):
        # REQ: SRS-CTL-041, SRS-SEC-006
        with Server(self.tmp, "--tls-cert", str(self.cert), "--tls-key", str(self.key)) as server:
            self.assertIn("TLS", server.banner)
            self.assertEqual(Ctl(server, ca=self.pki.ca).status()["state"], "idle")
            # Without --tls-ca the client speaks plain TCP, which a TLS server does not answer.
            code, _, _ = Ctl(server)("hello", seconds=40)
            self.assertEqual(code, 2)

    # [snippet:impostor]
    def check_refused(self, impostor_cert, impostor_key, host="127.0.0.1"):
        token = secret_file(self.tmp / "operator.token", "f" * 64)
        with ImpostorServer(impostor_cert, impostor_key) as impostor:
            fake = type("S", (), {"port": impostor.port, "env": dict(os.environ)})
            code, _, err = Ctl(fake, token_file=token, ca=self.pki.ca, host=host)("status")
        self.assertEqual(code, 2, err)
        self.assertIn("certificate", err.lower())
        self.assertEqual(impostor.received, b"", "the client sent data to a server it should not trust")
        return err
    # [/snippet:impostor]

    def test_the_client_sends_no_token_to_a_server_another_ca_signed(self):
        # REQ: SRS-CTL-041, SRS-SEC-007
        other = Pki(self.tmp / "other", name="impostor-ca")
        cert, key = other.server("impostor")
        self.check_refused(cert, key)

    def test_the_client_sends_no_token_to_a_server_certified_for_another_address(self):
        # REQ: SRS-CTL-041, SRS-SEC-007
        cert, key = self.pki.server("elsewhere", san="IP:10.0.0.7")
        self.check_refused(cert, key)


class Shutdown(SystemTest):
    def test_a_signal_during_a_run_stops_and_drains_it(self):
        # REQ: SRS-CTL-043
        cfg = write_json(self.tmp / "run.json", run_config(self.tmp, seconds=0))  # runs until stopped
        with Server(self.tmp, "--audit", str(self.tmp / "audit.jsonl")) as server:
            ctl = Ctl(server)
            ctl.ok("configure", str(cfg))
            ctl.ok("start")
            eventually(lambda: ctl.status()["sorter"]["singles_in"] > 0, 20, "the first singles")
            self.assertEqual(server.stop(), 0, server.output)
            self.assertIn("shutting down", server.output)
        audit = [json.loads(line) for line in (self.tmp / "audit.jsonl").read_text().splitlines()]
        actions = [(r["action"], r["who"]) for r in audit]
        # The run is stopped by the signal, drained, and only then does the server shut down.
        self.assertLess(actions.index(("stop", "signal")), actions.index(("run_ended", "service")))
        self.assertEqual(actions[-1], ("shutdown", "signal"))
        run_records = list(self.tmp.glob("st-*.run.json"))
        self.assertEqual(len(run_records), 1, "the stopped run was not closed")
        record = json.loads(run_records[0].read_text())
        self.assertTrue(record["run"]["integrity"]["complete"], record["run"]["integrity"])


class Startup(SystemTest):
    def test_the_server_refuses_a_public_address_without_tls_and_tokens(self):
        # REQ: SRS-SEC-005, SRS-CTL-043
        p = subprocess.run([app("minidaq_server"), "--port", "0", "--bind", "0.0.0.0"],
                           capture_output=True, text=True, timeout=30)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("TLS", p.stderr + p.stdout)

    def test_the_server_refuses_contradicting_options(self):
        # REQ: SRS-CTL-043
        tokens = write_json(self.tmp / "tokens.json", {"tokens": []})
        for args in (["--no-auth", "--tokens", str(tokens)], ["--tls-cert", "x.pem"], ["--port", "70000"]):
            p = subprocess.run([app("minidaq_server"), *args], capture_output=True, text=True, timeout=30)
            self.assertNotEqual(p.returncode, 0, args)
            self.assertTrue(p.stderr, args)

    def test_a_configuration_given_at_start_up_is_applied(self):
        # REQ: SRS-CTL-044
        cfg = write_json(self.tmp / "run.json", run_config(self.tmp))
        audit = self.tmp / "audit.jsonl"
        with Server(self.tmp, "--config", str(cfg), "--audit", str(audit)) as server:
            self.assertEqual(Ctl(server).status()["state"], "configured")
            self.assertEqual(server.stop(), 0, server.output)
        entries = [json.loads(line) for line in audit.read_text().splitlines()]
        self.assertIn(("configure", "command line"), [(e["action"], e["who"]) for e in entries])

    def test_an_invalid_configuration_at_start_up_is_refused(self):
        # REQ: SRS-CTL-044
        bad = write_json(self.tmp / "bad.json", dict(run_config(self.tmp), schema_version="0.1"))
        for path in (bad, self.tmp / "missing.json"):
            p = subprocess.run([app("minidaq_server"), "--port", "0", "--config", str(path)],
                               capture_output=True, text=True, timeout=30, env=dict(os.environ,
                               MINIDAQ_RUNTIME_DIR=str(self.tmp)))
            self.assertNotEqual(p.returncode, 0, path)
            self.assertIn(str(path), p.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=1)

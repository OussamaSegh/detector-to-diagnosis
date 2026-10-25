# SPDX-License-Identifier: MIT
"""Support for MiniDAQ's system tests (Chapter 19).

A system test runs the shipped programs as an operator would: minidaq_server in its own
process, minidaq_ctl to command it, minidaq_send to play a readout board, and minidaq_listmode
to check the files. Nothing is linked into the test; what it sees is what the programs print,
the files they write and their exit status. CTest sets MINIDAQ_APPS to the directory of the
programs and runs each test file on its own.

The helpers here keep every test isolated: each server gets a free port (--port 0), its own
runtime directory for the start-up token (MINIDAQ_RUNTIME_DIR) and its own output directory,
and every wait has a deadline, so a test fails instead of hanging (coding standard rule 5.5).
"""
import json
import os
import pathlib
import re
import select
import signal
import struct
import subprocess
import tempfile
import time
import unittest

APPS = pathlib.Path(os.environ.get("MINIDAQ_APPS", "build/debug/minidaq/apps"))
# Sanitizer builds run the programs several times slower; one factor stretches every deadline.
SLOW = float(os.environ.get("MINIDAQ_TEST_TIME_FACTOR", "1"))
READY = re.compile(r"control API on [\d.]+:(\d+) \(")


def app(name):
    path = APPS / name
    if not path.is_file():  # a test that skips when a program is missing would pass for no reason
        raise AssertionError(f"{path} not found: set MINIDAQ_APPS to the directory of the programs")
    return str(path)


def deadline(seconds):
    return time.monotonic() + seconds * SLOW


def eventually(condition, seconds, what):
    """Polls condition() until it is true; fails with `what` after `seconds` (times SLOW)."""
    end = deadline(seconds)
    while not condition():
        if time.monotonic() > end:
            raise AssertionError(f"timed out after {seconds * SLOW:.0f} s waiting for {what}")
        time.sleep(0.05)  # sleep: poll


class Server:
    """minidaq_server in its own process. Use as a context manager; stop() returns its exit status."""

    def __init__(self, workdir, *args, env=None):
        self.workdir = pathlib.Path(workdir)
        self.runtime = self.workdir / "runtime"
        self.runtime.mkdir(mode=0o700, exist_ok=True)
        self.env = dict(os.environ, MINIDAQ_RUNTIME_DIR=str(self.runtime), **(env or {}))
        self.args = [app("minidaq_server"), "--port", "0", *args]
        self.proc = None
        self.port = None
        self.banner = ""
        self.output = ""

    def __enter__(self):
        self.proc = subprocess.Popen(self.args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     text=True, env=self.env)
        end = deadline(10)
        while self.port is None:
            if self.proc.poll() is not None:
                raise AssertionError(f"minidaq_server exited with {self.proc.returncode}: "
                                     f"{self.proc.stdout.read()}")
            if time.monotonic() > end:
                self.proc.kill()
                raise AssertionError("minidaq_server did not report its port within 10 s")
            ready, _, _ = select.select([self.proc.stdout], [], [], 0.1)
            if ready:
                self.banner = self.proc.stdout.readline()
                m = READY.search(self.banner)
                if m:
                    self.port = int(m.group(1))
        return self

    def __exit__(self, *exc):
        if self.proc.poll() is None:
            self.stop()

    @property
    def token_file(self):
        return self.runtime / f"minidaq-{self.port}.token"

    def stop(self, sig=signal.SIGTERM, seconds=30):
        """Sends sig, waits for the exit and returns the exit status; the output is in self.output."""
        self.proc.send_signal(sig)
        try:
            rest, _ = self.proc.communicate(timeout=seconds * SLOW)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            rest, _ = self.proc.communicate()
            raise AssertionError(f"minidaq_server did not exit within {seconds * SLOW:.0f} s of {sig}")
        self.output = self.banner + rest
        return self.proc.returncode


class Ctl:
    """minidaq_ctl against one server. Each call returns (exit status, parsed response or None, stderr)."""

    def __init__(self, server, token_file=None, ca=None, host="127.0.0.1"):
        self.server = server
        self.options = ["--host", host, "--port", str(server.port)]
        if token_file is not None:
            self.options += ["--token-file", str(token_file)]
        if ca is not None:
            self.options += ["--tls-ca", str(ca)]

    def __call__(self, *command, seconds=30):
        p = subprocess.run([app("minidaq_ctl"), *self.options, *command], capture_output=True,
                           text=True, env=self.server.env, timeout=seconds * SLOW)
        try:
            response = json.loads(p.stdout) if p.stdout.lstrip().startswith("{") else None
        except json.JSONDecodeError:
            response = None
        return p.returncode, response, p.stderr

    def ok(self, *command, seconds=30):
        """Runs a command that must succeed and returns the response."""
        code, response, err = self(*command, seconds=seconds)
        if code != 0:
            raise AssertionError(f"minidaq_ctl {' '.join(command)} exited {code}: {response} {err}")
        return response

    def status(self):
        return self.ok("status")["status"]

    def run(self, config_path, seconds=60):
        """configure, start, and wait until the run has ended by itself; returns the final status."""
        self.ok("configure", str(config_path))
        self.ok("start")
        code, _, err = self("wait", "configured", str(seconds * SLOW), seconds=seconds + 30)
        if code != 0:
            raise AssertionError(f"the run did not end within {seconds * SLOW:.0f} s: {err}")
        return self.status()


def write_json(path, value):
    path = pathlib.Path(path)
    path.write_text(json.dumps(value, indent=1) + "\n")
    return path


def run_config(directory, prefix="st", rate_hz=1e6, seconds=1.0, seed=1, **sections):
    """A configuration for a synthetic run that writes list mode into directory."""
    cfg = {
        "schema_version": "1.3",
        "description": "system test",
        "source": {"rate_hz": rate_hz, "seed": seed},
        "stop_after_s": seconds,
        "output": {"type": "listmode", "directory": str(directory), "prefix": prefix},
    }
    for key, value in sections.items():
        cfg.setdefault(key, {}).update(value)
    return cfg


class Pki:
    """A test certificate authority and server certificates, made with the openssl command."""

    def __init__(self, directory, name="test-ca"):
        self.dir = pathlib.Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.ca_key = self.dir / f"{name}.key"
        self.ca = self.dir / f"{name}.pem"
        self._openssl("req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256",
                      "-nodes", "-keyout", self.ca_key, "-out", self.ca, "-days", "2",
                      "-subj", f"/CN={name}", "-addext", "basicConstraints=critical,CA:TRUE",
                      "-addext", "keyUsage=critical,keyCertSign,cRLSign")

    def server(self, name, san="IP:127.0.0.1"):
        """(certificate, key) for a server, signed by this CA, valid for san."""
        key, csr, cert = (self.dir / f"{name}.{ext}" for ext in ("key", "csr", "pem"))
        ext = self.dir / f"{name}.ext"
        ext.write_text(f"subjectAltName={san}\nextendedKeyUsage=serverAuth\n")
        self._openssl("req", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256", "-nodes",
                      "-keyout", key, "-out", csr, "-subj", f"/CN={name}")
        self._openssl("x509", "-req", "-in", csr, "-CA", self.ca, "-CAkey", self.ca_key,
                      "-CAcreateserial", "-out", cert, "-days", "2", "-extfile", ext)
        return cert, key

    @staticmethod
    def _openssl(*args):
        p = subprocess.run(["openssl", *map(str, args)], capture_output=True, text=True)
        if p.returncode != 0:
            raise AssertionError(f"openssl {args[0]} failed: {p.stderr}")


# MDQ-L1 (docs/formats/mdq-l1.md, minidaq/include/minidaq/format/list_mode.hpp)
FILE_MAGIC = b"MDQL\r\n\x1a\n"
BLOCK = struct.Struct("<4sIIIqII")
RECORD = struct.Struct("<IHHiHH")
TAG_CRYSTAL = 0x7FFF


def read_listmode(paths):
    """Every coincidence record of the files, in order, as tuples
    (time_ps, crystal_a, crystal_b, delayed, dt_ps, energy_a_kev, energy_b_kev). Tags are skipped.
    The reader trusts the files: check them with `minidaq_listmode verify` first."""
    for path in paths:
        data = pathlib.Path(path).read_bytes()
        if data[:8] != FILE_MAGIC:
            raise AssertionError(f"{path}: not an MDQ-L1 file")
        (header_bytes,) = struct.unpack_from("<I", data, 12)
        pos = header_bytes
        while pos + BLOCK.size <= len(data):
            magic, _seq, count, _flags, base, _pcrc, _hcrc = BLOCK.unpack_from(data, pos)
            if magic != b"MDQB":
                raise AssertionError(f"{path}: no block at offset {pos}")
            pos += BLOCK.size
            for off, a, b, dt, ea, eb in RECORD.iter_unpack(data[pos:pos + count * RECORD.size]):
                if a & TAG_CRYSTAL == TAG_CRYSTAL:
                    continue
                yield base + off, a & TAG_CRYSTAL, b, bool(a & 0x8000), dt, ea / 32, eb / 32
            pos += count * RECORD.size


def run_files(directory, prefix):
    """(the run's list-mode files in order, its run record) of the one run with prefix in directory."""
    records = sorted(pathlib.Path(directory).glob(f"{prefix}-*.run.json"))
    if len(records) != 1:
        raise AssertionError(f"expected one run record for {prefix} in {directory}, found {records}")
    record = json.loads(records[0].read_text())
    return [pathlib.Path(directory) / f for f in record["files"]], record


class SystemTest(unittest.TestCase):
    """A test case with a fresh temporary directory in self.tmp."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="minidaq-st-")
        self.tmp = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

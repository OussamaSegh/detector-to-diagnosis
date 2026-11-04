#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""MiniDAQ end to end (Chapter 33): one command from the detector to the image, with every hand-off
between the stages checked.

Two acquisitions run through the shipped programs, as an operator and the scanner would run them:

1. Daily QC: a point source at the center, sent by minidaq_send over the UDP readout link to
   minidaq_server, written as list mode; the QC report of Chapter 31 must pass.
2. Phantom: a 90 mm water cylinder with an 80 mm cylinder of activity, the same way; the files
   are binned into sinograms (minidaq_listmode sino), corrected for randoms and attenuation
   (Chapter 27) and reconstructed by OSEM (Chapter 28); the image must show the cylinder where
   it is.

For each acquisition the same singles are also sorted offline by minidaq_sim --link 1, which
quantizes them as the link does: that is the reference. With a clean link, the server's
coincidence records must equal the reference's, record for record. Between the stages, the
counters must add up: what the sender sent, the link delivered, the sorter took in and split,
the sink wrote, the files hold and the sinograms binned (accounting(), below).

    MINIDAQ_RECON_CPP=build/release/recon python3 tools/e2e.py build/release/minidaq/apps OUT
    ... tools/e2e.py APPS OUT --loss 0.001     # a damaged link: accounted for, run incomplete

Writes OUT/e2e.json (every check with its values), OUT/e2e.md, OUT/qc/ (the QC report),
OUT/image.npy, and OUT/manifest.json (SHA-256 of every file the run produced). Exits 1 if a check
fails, 2 on wrong usage.
"""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import platform
import re
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "minidaq/tests/system"))
sys.path.insert(0, str(ROOT))
import systest  # noqa: E402  (the system tests' helpers: Server, Ctl, list-mode reader)

UDP_PORT = re.compile(r"UDP readout on [\d.]+:(\d+)")
RECEIVE_BUFFER = re.compile(r"receive buffer (\d+) B")

# The sorter of both chains: minidaq_sim's defaults, given to the server explicitly.
WINDOW_PS = 4000
DELAY_PS = 100000
ENERGY_KEV = (435.0, 650.0)

PHANTOM_MM = 90.0       # water cylinder; the activity fills 80 mm of it (minidaq_send, minidaq_sim)
ACTIVE_RADIUS_MM = 80.0
LOR_RADIUS_MM = 156.0   # the lines at the mean depth of interaction (Chapter 28)
RADIUS_TOLERANCE_MM = 2.0
FLATNESS_TOLERANCE = 0.10  # center (r < 24 mm) over periphery (24 to 48 mm): 1 within this


# [snippet:check]
def check(name, left, right, equation, ok=None):
    """One check: two numbers that must agree (or ok given), and the equation that relates them."""
    return {"name": name, "equation": equation, "left": left, "right": right,
            "ok": bool(left == right) if ok is None else bool(ok)}
# [/snippet:check]


# [snippet:accounting]
def accounting(sent, status, records, sino):
    """The conservation checks between the stages of one acquisition.

    sent: what minidaq_send reported (singles, packets and the damage it injected); status: the
    server's final status; records: (prompts, delayed) counted in the list-mode files; sino: what
    minidaq_listmode sino reported. Each stage's input must be the previous stage's output, and each
    stage's output must be split exactly into what it passed on and what it set aside and counted.
    """
    link, s, sink = status["detector_counters"], status["sorter"], status["sink_counters"]
    damaged = sent["lost"] + sent["delayed"] + sent["duplicated"] > 0
    out = []
    if not damaged:
        out.append(check("link: every packet sent was delivered", link["packets_delivered"],
                         sent["packets"], "packets delivered = packets sent"))
        out.append(check("link: every single sent was delivered", link["words_delivered"],
                         sent["singles"], "words delivered = singles sent"))
    out.append(check("link: delivered or lost", link["packets_delivered"] + link["packets_lost"],
                     sent["packets"], "delivered + lost = packets sent"))
    out.append(check("link: received is delivered or stale", link["packets_received"],
                     link["packets_delivered"] + link["packets_stale"],
                     "received = delivered + stale"))
    out.append(check("decoder: every word delivered reached the sorter", s["singles_in"],
                     link["words_delivered"] - link.get("words_invalid", 0),
                     "sorter singles in = words delivered - invalid words"))
    split = (s["energy_rejected"] + s["out_of_order"] + s["singles_alone"] + 2 * s["pair_windows"]
             + s["singles_in_multiples"])
    out.append(check("sorter: every single is accounted for", split, s["singles_in"],
                     "energy rejected + out of order + alone + 2 x pair windows + in multiples "
                     "= singles in"))
    out.append(check("sorter: every pair window is a prompt or rejected by geometry",
                     s["prompts"] + s["geometry_rejected"], s["pair_windows"],
                     "prompts + geometry rejected = pair windows"))
    out.append(check("sink: every coincidence was written", sink["coincidences"],
                     s["prompts"] + s["delayed"], "written = prompts + delayed"))
    out.append(check("files: the records are the prompts and delayed counted",
                     list(records), [s["prompts"], s["delayed"]],
                     "(prompts, delayed) in the files = (prompts, delayed) of the sorter"))
    binned = (sino["prompts"] + sino["delayeds"] + sino["outside_fov"] + sino["above_mrd"]
              + sino["tof_outside"] + sino["no_angle"] + sino["invalid"])
    out.append(check("sinograms: every record binned or set aside", binned, sum(records),
                     "binned + outside FOV + above ring difference + outside TOF + no angle "
                     "+ invalid = records"))
    out.append(check("integrity: the run says whether it is complete",
                     status["integrity"]["complete"], not damaged,
                     "complete = no damage injected"))
    return out
# [/snippet:accounting]


SINO = re.compile(r"binned (\d+) prompts, (\d+) delayeds; outside the FOV (\d+), above the ring "
                  r"difference (\d+), outside the TOF range (\d+), no angle (\d+), invalid (\d+)")


def parse_sino(text):
    m = SINO.search(text)
    if not m:
        raise ValueError(f"minidaq_listmode sino: no summary in {text!r}")
    keys = ("prompts", "delayeds", "outside_fov", "above_mrd", "tof_outside", "no_angle", "invalid")
    return dict(zip(keys, map(int, m.groups())))


def parse_send(text):
    report = {"singles": int(re.search(r"singles (\d+)", text).group(1)),
              "packets": int(re.search(r"packets (\d+) of", text).group(1)),
              "lost": 0, "delayed": 0, "duplicated": 0, "both": 0}
    m = re.search(r"injected: lost (\d+), delayed (\d+), duplicated (\d+), both delayed and "
                  r"duplicated (\d+)", text)
    if m:
        report.update(lost=int(m.group(1)), delayed=int(m.group(2)), duplicated=int(m.group(3)),
                      both=int(m.group(4)))
    return report


def run(*args, timeout=600):
    p = subprocess.run([str(a) for a in args], capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"{' '.join(map(str, args))} exited {p.returncode}:\n{p.stdout}{p.stderr}")
    return p.stdout


def records_digest(files):
    """(prompts, delayed, SHA-256 of every record) of list-mode files, tags skipped."""
    h = hashlib.sha256()
    prompts = delayed = 0
    for rec in systest.read_listmode(files):
        h.update(repr(rec).encode())
        if rec[3]:
            delayed += 1
        else:
            prompts += 1
    return prompts, delayed, h.hexdigest()


def source_args(kind):
    """minidaq_send's and minidaq_sim's options for the same source."""
    if kind == "point":
        return ["--phantom", "0"], ["--source", "point", "--phantom", "0"]
    return ["--phantom", f"{PHANTOM_MM:g}"], ["--source", "cylinder", "--phantom", f"{PHANTOM_MM:g}"]


def server_config(directory, prefix):
    return {
        "schema_version": "1.4",
        "description": f"end to end, {prefix}",
        "source": {"type": "udp", "udp": {"address": "127.0.0.1", "port": 0,
                                          "receive_buffer_bytes": 16 << 20}},
        "pipeline": {"coincidence_window_ps": WINDOW_PS},
        "sorter": {"delay_ps": DELAY_PS, "energy_low_kev": ENERGY_KEV[0],
                   "energy_high_kev": ENERGY_KEV[1], "multiples": "kill_all",
                   "min_sector_difference": 1, "mode": "fixed"},
        "output": {"type": "listmode", "directory": str(directory), "prefix": prefix},
    }


# [snippet:acquire]
def acquire(apps, work, name, kind, args):
    """One acquisition through the server and, from the same seed, the offline reference.
    Returns a dict with the counters, the checks and the times of the stages."""
    d = work / name
    ref = work / f"{name}-reference"
    d.mkdir(parents=True)
    ref.mkdir(parents=True)
    send_src, sim_src = source_args(kind)
    common = ["--activity", f"{args.activity if kind == 'phantom' else args.qc_activity:g}",
              "--seconds", f"{args.seconds:g}", "--seed", str(args.seed)]
    faults = ["--loss", f"{args.loss:g}", "--reorder", f"{args.reorder:g}",
              "--duplicate", f"{args.duplicate:g}"]
    times = {}

    t = time.monotonic()
    run(apps / "minidaq_sim", *common, *sim_src, "--link", "1", "--listmode", ref)
    times["reference"] = time.monotonic() - t

    cfg = systest.write_json(work / f"{name}.json", server_config(d, name))
    t = time.monotonic()
    with systest.Server(work) as server:
        ctl = systest.Ctl(server)
        ctl.ok("configure", str(cfg))
        ctl.ok("start")
        detector = ctl.status()["detector"]
        port = int(UDP_PORT.search(detector).group(1))
        sent = parse_send(run(apps / "minidaq_send", "--port", port, *common, *send_src, *faults,
                              "--speed", f"{args.speed:g}"))
        expected = sent["packets"] - sent["lost"] + sent["duplicated"]
        systest.eventually(lambda: ctl.status()["detector_counters"]["datagrams"] >= expected, 60,
                           f"{expected} datagrams at the server")
        ctl.ok("stop")
        systest.eventually(lambda: ctl.status()["state"] == "configured", 60, "the end of the run")
        status = ctl.status()
        code = server.stop()
    times["acquisition"] = time.monotonic() - t

    files, record = systest.run_files(d, name)
    t = time.monotonic()
    run(apps / "minidaq_listmode", "verify", *files)
    prompts, delayed, digest = records_digest(files)
    ref_files, _ = systest.run_files(ref, "minidaq")
    ref_prompts, ref_delayed, ref_digest = records_digest(ref_files)
    times["verify"] = time.monotonic() - t

    t = time.monotonic()
    sino = parse_sino(run(apps / "minidaq_listmode", "sino", "--out", d / "sino", *files))
    times["sinograms"] = time.monotonic() - t

    checks = [check("server: exit status", code, 0, "exit status = 0"),
              check("server: no fault", status["fault"], None, "fault = none"),
              check("server: no stage dropped a batch", sum(x["dropped"] for x in status["stages"]),
                    0, "dropped batches = 0"),
              check("server: no late single", status["late_singles"], 0, "late singles = 0")]
    checks += accounting(sent, status, (prompts, delayed), sino)
    damaged = sent["lost"] + sent["delayed"] + sent["duplicated"] > 0
    if damaged:
        # No comparison with the reference: a lost single can remove a coincidence, and it can
        # also add one, by turning a multiple that the sorter kills into a pair. The accounting
        # above and the integrity verdict are what a damaged run must get right.
        lost = "/detector_counters/packets_lost"
        checks.append(check("integrity: the loss is named", lost,
                            [x["counter"] for x in status["integrity"]["losses"]],
                            "packets_lost in the losses",
                            ok=lost in [x["counter"] for x in status["integrity"]["losses"]]
                            or sent["lost"] == 0))
    else:
        checks.append(check("reference: the server wrote the reference's records", digest,
                            ref_digest, "SHA-256 of the records = SHA-256 of the reference's"))
    latency = status.get("latency_ns", {}).get("end_to_end", {})
    return {"name": name, "source": kind, "directory": str(d), "record": str(record["run_name"]),
            "sent": sent, "sorter": status["sorter"], "link": status["detector_counters"],
            "sink": status["sink_counters"], "records": {"prompts": prompts, "delayed": delayed},
            "reference": {"prompts": ref_prompts, "delayed": ref_delayed},
            "sinogram": sino, "latency_ms": {k: latency[k] / 1e6 for k in ("p50", "p99", "max")
                                             if k in latency},
            "checks": checks, "seconds": times}
# [/snippet:acquire]


def daily_qc(acq, out):
    """The QC report of Chapter 31 on the point-source acquisition; its verdict is one check."""
    d = pathlib.Path(acq["directory"])
    record = next(d.glob("*.run.json"))
    env = dict(os.environ, PYTHONPATH=str(ROOT / "analysis/src"))
    t = time.monotonic()
    p = subprocess.run([sys.executable, "-m", "minidaq_analysis", str(record), str(out / "qc")],
                       capture_output=True, text=True, env=env, timeout=600)
    acq["seconds"]["qc"] = time.monotonic() - t
    path = out / "qc" / "report.json"
    if not path.exists():  # the QC tool did not get as far as a report: its error is the evidence
        acq["qc"] = {"result": "ERROR", "stderr": p.stderr[-2000:]}
        acq["checks"].append(check("QC: the daily QC report passes", "no report", "PASS",
                                   f"QC result = PASS (exit status {p.returncode}: "
                                   f"{(p.stderr.strip().splitlines() or ['no output'])[-1]})"))
        return
    report = json.loads(path.read_text())
    result = "PASS" if report["passed"] else "FAIL"
    acq["qc"] = {"result": result, "checks": {c["name"]: c["value"] for c in report["checks"]}}
    acq["checks"].append(check("QC: the daily QC report passes", result, "PASS",
                               f"QC result = PASS (exit status {p.returncode})"))


# [snippet:image]
def reconstruct(acq, out, iterations=4, subsets=8, n=128, pixel_mm=2.0):
    """OSEM of the phantom's sinograms with randoms (from the singles) and attenuation in the model,
    then two checks on the image: the cylinder's radius from its profile, and its uniformity."""
    import numpy as np  # noqa: PLC0415  (only this step needs numpy)

    from tools.recon import chain, corrections as cor, mlem, project, sinogram as sg  # noqa: PLC0415

    t = time.monotonic()
    d = pathlib.Path(acq["directory"])
    h = sg.read_header(d / "sino.hdr")
    y = sg.read(h, "prompts").sum(axis=0)
    r = chain.randoms(d, h).sum(axis=0)
    att = cor.attenuation_factors(h, PHANTOM_MM).sum(axis=0)
    s, phi = project.bin_lines(h, LOR_RADIUS_MM)
    try:
        proj = project.CppProjector(s, phi, n=n, pixel_mm=pixel_mm)
        which = "C++"
    except ImportError:
        proj = project.Projector(s, phi, n=n, pixel_mm=pixel_mm)
        which = "numpy"
    img = mlem.osem(y, proj, att, r, iterations, n_subsets=subsets)
    np.save(out / "image.npy", img)
    xs, ys = proj.pixel_centers()
    radius = np.hypot(xs, ys)
    edges = np.arange(0.0, 120.0 + pixel_mm, pixel_mm)
    which_ring = np.digitize(radius, edges) - 1
    profile = np.array([img[which_ring == k].mean() for k in range(len(edges) - 1)])
    centers = 0.5 * (edges[:-1] + edges[1:])
    plateau = img[radius < 0.6 * ACTIVE_RADIUS_MM]
    level = 0.5 * plateau.mean()
    k = int(np.argmax((profile < level) & (centers > 0.5 * ACTIVE_RADIUS_MM)))
    r_half = centers[k - 1] + (profile[k - 1] - level) / (profile[k - 1] - profile[k]) * pixel_mm
    # Without attenuation correction the center of a water cylinder comes out low ("cupping"):
    # the ratio of the inner disc to the ring around it is about 0.86 here; with it, about 1.
    ratio = float(img[radius < 24.0].mean() / img[(radius >= 24.0) & (radius < 48.0)].mean())
    # Noise, for the record: the spread of 8 mm x 8 mm block means inside 0.6 x the radius.
    b = 4
    blocks = img.reshape(n // b, b, n // b, b).mean(axis=(1, 3))
    bc = np.hypot(xs.reshape(n // b, b, n // b, b).mean(axis=(1, 3)),
                  ys.reshape(n // b, b, n // b, b).mean(axis=(1, 3)))
    inside = blocks[bc < 0.6 * ACTIVE_RADIUS_MM]
    acq["seconds"]["reconstruction"] = time.monotonic() - t
    acq["image"] = {"projector": which, "iterations": iterations, "subsets": subsets,
                    "pixels": n, "pixel_mm": pixel_mm, "radius_at_half_mm": round(float(r_half), 2),
                    "center_over_periphery": round(ratio, 4),
                    "block_cv": round(float(inside.std() / inside.mean()), 4),
                    "prompts_binned": int(y.sum()), "randoms_estimated": round(float(r.sum()), 1)}
    acq["checks"].append(check("image: the cylinder's radius at half its level",
                               round(float(r_half), 2), ACTIVE_RADIUS_MM,
                               f"abs(radius - {ACTIVE_RADIUS_MM:g} mm) <= {RADIUS_TOLERANCE_MM:g} mm",
                               ok=abs(r_half - ACTIVE_RADIUS_MM) <= RADIUS_TOLERANCE_MM))
    acq["checks"].append(check("image: flat inside the cylinder (attenuation corrected)",
                               round(ratio, 4), 1.0,
                               f"abs(center / periphery - 1) <= {FLATNESS_TOLERANCE:g}",
                               ok=abs(ratio - 1.0) <= FLATNESS_TOLERANCE))


# [/snippet:image]


def manifest(out):
    files = sorted(p for p in out.rglob("*") if p.is_file() and p.name != "manifest.json")
    return {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def git_commit():
    p = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                       capture_output=True, text=True)
    dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=no"],
                           capture_output=True, text=True).stdout.strip()
    return (p.stdout.strip() or "unknown") + ("-dirty" if dirty else "")


def markdown(result):
    lines = [f"# MiniDAQ end to end: {'PASS' if result['ok'] else 'FAIL'}", "",
             f"{result['time']}, commit {result['commit']}, {result['machine']}.", "",
             f"Command: `{result['command']}`", ""]
    for acq in result["acquisitions"]:
        sent = acq["sent"]
        lines += [f"## {acq['name']} ({acq['source']})", "",
                  f"{sent['singles']:,} singles in {sent['packets']:,} packets; "
                  f"{acq['records']['prompts']:,} prompts and {acq['records']['delayed']:,} delayed "
                  f"written; end-to-end latency p99 {acq['latency_ms'].get('p99', 0):.2f} ms, "
                  f"max {acq['latency_ms'].get('max', 0):.2f} ms.", "",
                  "| Check | Equation | Values | Result |", "|---|---|---|---|"]
        for c in acq["checks"]:
            values = f"{c['left']} / {c['right']}"
            if len(values) > 40:
                values = f"{str(c['left'])[:16]}... / {str(c['right'])[:16]}..."
            lines.append(f"| {c['name']} | {c['equation']} | {values} | "
                         f"{'pass' if c['ok'] else 'FAIL'} |")
        times = ", ".join(f"{k} {v:.1f} s" for k, v in acq["seconds"].items())
        lines += ["", f"Times: {times}.", ""]
        if "image" in acq:
            im = acq["image"]
            lines += [f"Image: OSEM ({im['projector']} projector), {im['iterations']} iterations of "
                      f"{im['subsets']} subsets, {im['pixels']} x {im['pixels']} pixels of "
                      f"{im['pixel_mm']:g} mm; radius at half level {im['radius_at_half_mm']} mm, "
                      f"center over periphery {im['center_over_periphery']}, coefficient of "
                      f"variation of 8 mm blocks {im['block_cv']}.", ""]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("apps", type=pathlib.Path, help="directory of the MiniDAQ programs")
    ap.add_argument("out", type=pathlib.Path, help="directory for the results (created)")
    ap.add_argument("--activity", type=float, default=5e6, help="phantom activity, Bq")
    ap.add_argument("--qc-activity", type=float, default=1e6, help="point source activity, Bq")
    ap.add_argument("--seconds", type=float, default=2.0, help="detector time of each acquisition")
    ap.add_argument("--seed", type=int, default=33)
    ap.add_argument("--speed", type=float, default=1.0,
                    help="1 sends in detector time, 0 as fast as possible")
    ap.add_argument("--loss", type=float, default=0.0)
    ap.add_argument("--reorder", type=float, default=0.0)
    ap.add_argument("--duplicate", type=float, default=0.0)
    ap.add_argument("--no-image", action="store_true", help="skip the reconstruction (no numpy)")
    ap.add_argument("--quiet", action="store_true", help="print only the failed checks")
    args = ap.parse_args(argv)
    systest.APPS = args.apps.resolve()
    apps = args.apps.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    started = datetime.datetime.now(datetime.timezone.utc)
    with tempfile.TemporaryDirectory(prefix="minidaq-e2e-") as tmp:
        work = pathlib.Path(tmp)
        qc = acquire(apps, work, "qc", "point", args)
        daily_qc(qc, out)
        phantom = acquire(apps, work, "phantom", "phantom", args)
        if not args.no_image:
            reconstruct(phantom, out)
        for acq in (qc, phantom):  # the run records travel with the results
            for f in pathlib.Path(acq["directory"]).glob("*.run.json"):
                (out / f"{acq['name']}.run.json").write_bytes(f.read_bytes())
            acq["directory"] = acq["name"]
    acquisitions = [qc, phantom]
    result = {"format": "MiniDAQ end-to-end result", "version": 1,
              "time": started.strftime("%Y-%m-%dT%H:%M:%SZ"), "commit": git_commit(),
              "machine": f"{platform.machine()}, {os.cpu_count()} CPUs",
              "command": "tools/e2e.py " + " ".join(sys.argv[1:] if argv is None else argv),
              "ok": all(c["ok"] for a in acquisitions for c in a["checks"]),
              "acquisitions": acquisitions}
    (out / "e2e.json").write_text(json.dumps(result, indent=1) + "\n")
    (out / "e2e.md").write_text(markdown(result) + "\n")
    (out / "manifest.json").write_text(json.dumps(manifest(out), indent=1) + "\n")
    failed = [f"{a['name']}: {c['name']}" for a in acquisitions for c in a["checks"] if not c["ok"]]
    if not args.quiet:
        print(markdown(result))
    for f in failed:
        print(f"FAIL {f}", file=sys.stderr)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())

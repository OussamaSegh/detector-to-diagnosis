"""Where this variant's ADRs are. The reference solution's records are MiniDAQ's own."""
import pathlib

ADR_DIR = pathlib.Path(__file__).resolve().parents[4] / "docs" / "adr"

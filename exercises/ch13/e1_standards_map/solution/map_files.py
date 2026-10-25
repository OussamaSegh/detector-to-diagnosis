"""Where this variant's standards map is (the tests import this module)."""
import pathlib

MAP = pathlib.Path(__file__).resolve().parent / "standards.dot"

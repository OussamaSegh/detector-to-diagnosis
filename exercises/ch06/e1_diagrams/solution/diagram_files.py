"""Where this variant's diagrams are (the tests import this module)."""
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
STATES = HERE / "states.dot"
COMPONENTS = HERE / "components.dot"

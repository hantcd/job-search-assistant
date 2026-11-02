"""Import a skill's script as a module, by path (skills aren't packages)."""
import importlib.util
import os
import sys
import warnings

warnings.simplefilter("ignore", ResourceWarning)  # scripts read small files with open().read()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "tests", "fixtures")


def load(skill, name):
    folder = os.path.join(ROOT, "skills", skill)
    if folder not in sys.path:
        sys.path.insert(0, folder)
    spec = importlib.util.spec_from_file_location("%s_%s" % (skill.replace("-", "_"), name),
                                                  os.path.join(folder, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fixture(*parts):
    return os.path.join(FIX, *parts)

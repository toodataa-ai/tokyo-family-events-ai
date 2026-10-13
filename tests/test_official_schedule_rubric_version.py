import importlib.util
from pathlib import Path
import unittest

class NewPromptRubricMappingTests(unittest.TestCase):
    def test_all_version_12_through_15_use_family_fit_v2(self):
        path=Path(__file__).resolve().parents[1]/"tools"/"validate_decisions.py"
        spec=importlib.util.spec_from_file_location("validate_decisions",path)
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for n in range(12,16):
            self.assertEqual(module.PROMPT_RUBRIC.get(f"v1.{n}"),"family-fit-v2")
        self.assertEqual(module.PROMPT_RUBRIC.get("v1.5"),"family-fit-v1")

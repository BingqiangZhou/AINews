#!/usr/bin/env python3
"""Structural integrity tests for the audio-to-social skill.

These tests do NOT check content quality (that is ``validate_content_quality``'s
job). They guard the skill's *plumbing* — the kind of drift a doc/script-heavy
repo silently accumulates:

- Every script / reference / agent file named in SKILL.md exists on disk.
- config.json parses and carries the required sections and load-bearing keys.
- config.json's ``schema_version`` matches what the validator hardcodes.

A rename, a deleted script, or a stale doc link fails here instead of breaking a
real run hours later. Run with::

    cd .zcode/skills/audio-to-social && python -m pytest scripts/test_e2e_structure.py -q
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
REFERENCES_DIR = SKILL_DIR / "references"
AGENTS_DIR = SKILL_DIR / "agents"
SKILL_MD = SKILL_DIR / "SKILL.md"
CONFIG_JSON = SKILL_DIR / "config.json"

# Pure-orchestrator (v5/v4-schema) config schema_version. Note: this is now
# DECOUPLED from validate_content_quality.py's hardcoded "audio-to-social-v3"
# — that validator is only reused by article-studio (which documents ignoring
# its STATE_SCHEMA false-positive). The orchestrator itself no longer runs that
# validator on its own state, so config.schema_version tracks the orchestrator
# config structure, not the validator's pin.
EXPECTED_CONFIG_SCHEMA_VERSION = "audio-to-social-v4"

_REQUIRED_CONFIG_SECTIONS = (
    "brand", "platforms", "content", "source", "tts", "cover",
    "image", "publishing", "environment",
)
_REQUIRED_CONFIG_KEYS = {
    "brand": ("name", "storage_root"),
    "platforms": ("default_target", "boker_next_episode"),
    "image": ("output_format", "cover_size", "illustration_size"),
    "environment": ("conda_python", "ffmpeg", "mimo_api_key_env"),
}


def _skill_md_text() -> str:
    return SKILL_MD.read_text(encoding="utf-8")


class SkillStructureTests(unittest.TestCase):
    def test_scripts_referenced_in_skill_md_exist(self) -> None:
        """Every ``{skill_dir}/scripts/<name>`` token in SKILL.md must resolve."""
        referenced = set(
            re.findall(r"scripts/([A-Za-z0-9_\-]+\.[A-Za-z0-9]+)", _skill_md_text())
        )
        missing = sorted(name for name in referenced if not (SCRIPTS_DIR / name).exists())
        self.assertEqual(
            missing, [], f"scripts referenced in SKILL.md but missing on disk: {missing}"
        )

    def test_references_referenced_in_skill_md_exist(self) -> None:
        """Every ``references/<name>.md`` link in SKILL.md must resolve."""
        referenced = set(re.findall(r"references/([A-Za-z0-9_\-]+\.md)", _skill_md_text()))
        missing = sorted(name for name in referenced if not (REFERENCES_DIR / name).exists())
        self.assertEqual(
            missing, [], f"references referenced in SKILL.md but missing on disk: {missing}"
        )

    def test_agents_referenced_in_skill_md_exist(self) -> None:
        """Every literal ``agents/<name>.md`` in SKILL.md must resolve.

        ``agents/{name}.md`` is a template (braces), intentionally skipped by the
        character class — only literal filenames are captured and checked.
        """
        referenced = set(re.findall(r"agents/([A-Za-z0-9_\-]+\.md)", _skill_md_text()))
        missing = sorted(name for name in referenced if not (AGENTS_DIR / name).exists())
        self.assertEqual(
            missing, [], f"agents referenced in SKILL.md but missing on disk: {missing}"
        )

    def test_config_json_has_required_sections_and_keys(self) -> None:
        cfg = json.loads(CONFIG_JSON.read_text(encoding="utf-8-sig"))
        for section in _REQUIRED_CONFIG_SECTIONS:
            self.assertIn(section, cfg, f"config.json missing required section: {section}")
        for section, keys in _REQUIRED_CONFIG_KEYS.items():
            for key in keys:
                self.assertIn(
                    key,
                    cfg.get(section, {}),
                    f"config.json missing required key: {section}.{key}",
                )

    def test_config_schema_version_is_current(self) -> None:
        """config.schema_version must match the orchestrator's current schema.

        The pure-orchestrator config is v4. (validate_content_quality.py still
        pins v3, but that validator is now only reused by article-studio, which
        ignores its STATE_SCHEMA false-positive; the orchestrator no longer
        runs it on its own state.)
        """
        cfg = json.loads(CONFIG_JSON.read_text(encoding="utf-8-sig"))
        self.assertEqual(
            cfg.get("schema_version"),
            EXPECTED_CONFIG_SCHEMA_VERSION,
            f"config.schema_version={cfg.get('schema_version')!r} but expected "
            f"{EXPECTED_CONFIG_SCHEMA_VERSION!r}.",
        )

    def test_state_schema_documents_v4_stages(self) -> None:
        """state-schema.md must document the v4 orchestrator stages.

        Guards against accidental regression to the old v3 phase1-7 structure
        after the pure-orchestrator refactor.
        """
        schema_text = (REFERENCES_DIR / "state-schema.md").read_text(encoding="utf-8")
        self.assertIn("audio-to-social-v4", schema_text)
        for stage in ("normalize", "transcribe", "article", "media", "podcast", "video", "archive"):
            self.assertIn(f'"{stage}"', schema_text, f"state-schema.md missing v4 stage: {stage}")

    def test_delegation_contracts_covers_four_downstream_skills(self) -> None:
        """delegation-contracts.md must document all 4 downstream skills."""
        contracts = (REFERENCES_DIR / "delegation-contracts.md").read_text(encoding="utf-8")
        for skill in ("article-studio", "article-cover-image-generator", "article-illustrator",
                      "article-to-solo-podcast", "article-to-video"):
            self.assertIn(skill, contracts, f"delegation-contracts.md missing skill: {skill}")


if __name__ == "__main__":
    unittest.main()

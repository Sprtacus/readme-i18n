"""readme_i18n.py
Translate a project's README into multiple languages using the DeepL API and
persist the results next to the original file. Designed to be used from a
pre‑commit hook but also works as a standalone CLI.

Author: Marius
"""

from __future__ import annotations

# Standard library ------------------------------------------------------------------
import argparse
import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

# Third‑party packages ---------------------------------------------------------------
try:
    import tomllib  # Python ≥ 3.11
except ModuleNotFoundError:  # Python ≤ 3.10
    import tomli as tomllib  # type: ignore

try:
    import deepl  # DeepL SDK
except ModuleNotFoundError:
    print("deepl package not installed. Install with 'pip install deepl'.", file=sys.stderr)
    sys.exit(1)

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Repository helpers
# ---------------------------------------------------------------------------

def detect_repo_root() -> Path:
    """Return the git repository root or *cwd* if we're not inside a git repo."""
    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return Path(root)
    except Exception:
        return Path.cwd()


REPO_ROOT: Path = detect_repo_root()
SCRIPT_DIR: Path = Path(__file__).resolve().parent
README_PATH: Path = REPO_ROOT / "README.md"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Config:
    """All tweakable parameters live here so they are easy to override via *pyproject.*"""

    source_lang: str = "EN"
    languages: List[str] = field(default_factory=lambda: ["DE"])
    output_dir: Path = REPO_ROOT / "translations"
    template: str = "{basename}.{lang}{ext}"
    header_template_path: Path = REPO_ROOT / ".readme-i18n-header.md"
    marker_start: str = "<!-- readme-i18n start -->"
    marker_end: str = "<!-- readme-i18n end -->"

    # ---------------------------------------------------------------------
    # Factory helpers
    # ---------------------------------------------------------------------

    @classmethod
    def load(cls) -> "Config":
        """Load overrides from *pyproject.toml* (section *[tool.readme-i18n]*) if present."""
        defaults = cls()
        pyproject = REPO_ROOT / "pyproject.toml"
        if not pyproject.exists():
            return defaults

        cfg = tomllib.load(pyproject.open("rb")).get("tool", {}).get("readme-i18n", {})
        return cls(
            source_lang=cfg.get("source_lang", defaults.source_lang),
            languages=cfg.get("languages", defaults.languages),
            output_dir=REPO_ROOT / cfg.get("output_dir", defaults.output_dir.name),
            template=cfg.get("template", defaults.template),
            header_template_path=REPO_ROOT / cfg.get("header_template_path", defaults.header_template_path.name),
            marker_start=cfg.get("marker_start", defaults.marker_start),
            marker_end=cfg.get("marker_end", defaults.marker_end),
        )


# ---------------------------------------------------------------------------
# Flag‑emoji mapping (used in the generated header)
# ---------------------------------------------------------------------------


def _load_flags() -> Dict[str, str]:
    """Return a *code → emoji* mapping. Falls back to an empty dict if not found."""
    for fp in (REPO_ROOT / "flags.json", SCRIPT_DIR.parent / "flags.json"):
        if fp.exists():
            try:
                data = json.load(fp.open())
                if isinstance(data, dict):
                    return {k.upper(): v for k, v in data.items()}
            except Exception as exc:
                logging.warning("Failed to load %s: %s", fp, exc)
    return {}


FLAGS: Dict[str, str] = _load_flags()
CREDIT_LINK = '<a href="https://github.com/Sprtacus/readme-i18n/">readme-i18n</a>'

# ---------------------------------------------------------------------------
# Segment protection (code blocks, inline code & emoji)
# ---------------------------------------------------------------------------

EMOJI_PATTERN = (
    "[\U0001F600-\U0001F64F]"      # Emoticons
    "|[\U0001F300-\U0001F5FF]"     # Symbols & Pictographs
    "|[\U0001F680-\U0001F6FF]"     # Transport & Map
    "|[\U0001F1E6-\U0001F1FF]{2}"  # Regional indicator (flags)
    "|[\U00002600-\U000026FF]"     # Misc symbols
    "|[\U00002700-\U000027BF]"     # Dingbats
    "|[\U0001F900-\U0001F9FF]"     # Supplemental symbols
    "|[\U0001FA70-\U0001FAFF]"     # Extended‑A
    "|[\U00002500-\U00002BEF]"     # Box drawing & co.
    "|[\U0001F018-\U0001F270]"     # Older pictographs
    "|[\U0001F000-\U0001F02F]"     # Mahjong & domino
)

EMOJI_MODIFIERS = "[\U0001F3FB-\U0001F3FF\U0000200D\U0000FE0F]"
FULL_EMOJI_PATTERN = rf"(?:{EMOJI_PATTERN})(?:{EMOJI_MODIFIERS})*"

EXCLUSION_PATTERN = re.compile(
    rf"""(
        ```[\s\S]*?```          # Fenced code‑block
      | `[^`\n]+`                # Inline code
      | {FULL_EMOJI_PATTERN}     # Emoji (with modifiers)
    )""",
    re.VERBOSE,
)


def protect_segments(text: str) -> Tuple[str, Dict[str, str]]:
    """Replace sensitive segments with sentinels so DeepL won't mangle them."""
    mapping: Dict[str, str] = {}
    counter = 0

    def _repl(match: re.Match[str]) -> str:  # type: ignore[type-var]
        nonlocal counter
        token = f"__RMI18N_{counter}__"
        mapping[token] = match.group(0)
        counter += 1
        return token

    cleaned = EXCLUSION_PATTERN.sub(_repl, text)
    return cleaned, mapping


def restore_segments(text: str, mapping: Dict[str, str]) -> str:
    """Undo *protect_segments* by substituting the original snippets back in."""
    for token, original in mapping.items():
        text = text.replace(token, original)
    return text

# ---------------------------------------------------------------------------
# Header helpers
# ---------------------------------------------------------------------------


def _load_header_template(cfg: Config) -> str:
    """Return the raw header template (ensuring start/end markers are present)."""
    if cfg.header_template_path.exists():
        raw = cfg.header_template_path.read_text("utf-8")
    else:
        raw = (
            "<p align=\"right\">\n  <strong>{languages_label}</strong> {links}<br>\n"
            "  <sub>{credit}</sub>\n</p>"
        )

    if cfg.marker_start not in raw:
        raw = f"{cfg.marker_start}\n{raw}"
    if cfg.marker_end not in raw:
        raw = f"{raw}\n{cfg.marker_end}"
    return raw


def _relpath(target: Path, base: Path) -> str:
    """Return a POSIX‑style relative path from *base* to *target*."""
    return os.path.relpath(target, base).replace(os.sep, "/")


def _build_links(cfg: Config, cur_file: Path) -> str:
    """Build the language switcher used in every generated header."""
    base = cur_file.parent
    parts: List[str] = []

    def _add(label: str, dest: Path, code: str) -> None:
        parts.append(f'<a href="{_relpath(dest, base)}">{FLAGS.get(code.upper(), "")} {label}</a>')

    _add(cfg.source_lang, README_PATH, cfg.source_lang)
    for code in cfg.languages:
        fname = cfg.template.format(basename=README_PATH.stem, lang=code, ext=README_PATH.suffix)
        _add(code, cfg.output_dir / fname, code)

    return " ·\n  ".join(parts)


def _translate(text: str, lang: str, tr: deepl.Translator | None) -> str:
    """Wrapper around DeepL to keep *None* translator or *EN* no‑ops concise."""
    if lang == "EN" or tr is None:
        return text
    try:
        return tr.translate_text(text, target_lang=lang).text
    except Exception:  # noqa: BLE001 – catching everything is deliberate here
        return text


def _build_header(cfg: Config, file_: Path, lang: str, tr: deepl.Translator | None) -> str:
    return _load_header_template(cfg).format(
        links=_build_links(cfg, file_),
        languages_label=_translate("Languages:", lang, tr),
        credit=_translate(f"generated with {CREDIT_LINK} using DeepL", lang, tr),
    )


def _strip_header(text: str, cfg: Config) -> str:
    """Remove a previously inserted header so we don't nest them on regen."""
    return re.sub(
        rf"{re.escape(cfg.marker_start)}[\s\S]*?{re.escape(cfg.marker_end)}\n?",
        "",
        text,
        flags=re.I,
    ).lstrip()


def ensure_header(path: Path, cfg: Config, lang: str, tr: deepl.Translator | None) -> bool:
    """Add (or update) the header of *path* in‑place. Returns *True* if changed."""
    original = path.read_text("utf-8") if path.exists() else ""
    body = _strip_header(original, cfg)
    new_content = f"{_build_header(cfg, path, lang, tr)}\n\n{body}".rstrip() + "\n"
    if new_content != original:
        path.write_text(new_content, "utf-8")
        logging.info("Header updated in %s", path.relative_to(REPO_ROOT))
        return True
    return False

# ---------------------------------------------------------------------------
# Translation helpers
# ---------------------------------------------------------------------------


def load_api_key() -> str | None:
    """Return *DEEPL_API_KEY* from either *.env* or the current environment."""
    load_dotenv()
    return os.getenv("DEEPL_API_KEY")


def translate_body(text: str, tr: deepl.Translator, lang: str) -> str | None:
    """Translate *text* to *lang* while safeguarding code blocks & emoji."""
    cleaned, mapping = protect_segments(text)
    try:
        translated = cleaned if lang == "EN" else tr.translate_text(cleaned, target_lang=lang).text
    except deepl.DeepLException as exc:
        logging.error("Error translating to %s: %s", lang, exc)
        return None
    return restore_segments(translated, mapping)


def build_translations(readme: Path, key: str, cfg: Config) -> List[Path]:
    """Return a list of newly generated translation files."""
    translator = deepl.Translator(key)
    source_body = _strip_header(readme.read_text("utf-8"), cfg)

    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    created: List[Path] = []
    for lang in cfg.languages:
        text = translate_body(source_body, translator, lang)
        if text is None:
            continue

        fname = cfg.template.format(basename=readme.stem, lang=lang, ext=readme.suffix)
        target = cfg.output_dir / fname
        target.write_text(text, "utf-8")
        logging.info("Generated %s", target.relative_to(REPO_ROOT))
        ensure_header(target, cfg, lang, translator)
        created.append(target)

    return created

# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: List[str] | None = None) -> int:  # noqa: C901 – "main" is allowed to be long
    """Parse CLI args, run translation workflow and exit with an appropriate code."""
    parser = argparse.ArgumentParser(
        description="Translate README via DeepL and maintain multilingual headers.",
    )
    parser.add_argument("files", nargs="*", help="Paths from pre-commit (optional).")
    parser.add_argument("--check", action="store_true", help="Exit 1 if README.md is staged.")
    args = parser.parse_args(argv)

    logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
    if os.getenv("README_I18N_DEBUG"):
        logging.getLogger().setLevel(logging.DEBUG)

    cfg = Config.load()
    logging.debug("Config: %s", cfg)

    # 1) Ensure the *source* README always has a header so that users see the language switcher.
    if ensure_header(README_PATH, cfg, cfg.source_lang, None):
        subprocess.run(["git", "add", str(README_PATH)], check=False)

    # 2) Determine the list of staged files (comes from pre‑commit when run via hook)
    staged = args.files or subprocess.getoutput("git diff --cached --name-only").splitlines()
    if README_PATH.name not in staged:
        logging.info("README.md not staged; nothing to do.")
        return 0

    # 3) When --check is supplied we bail out early so lint‑staged can fail the commit.
    if args.check:
        return 1

    # 4) Do the heavy lifting
    api_key = load_api_key()
    if not api_key:
        logging.warning("No DEEPL_API_KEY found – skipping translation.")
        return 0

    created = build_translations(README_PATH, api_key, cfg)
    if not created:
        return 1

    subprocess.run(["git", "add", *map(str, created)], check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())

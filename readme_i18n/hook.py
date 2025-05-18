from __future__ import annotations

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

try:
    import tomllib  # Python ≥ 3.11
except ModuleNotFoundError:  # Python ≤ 3.10
    import tomli as tomllib  # type: ignore

try:
    import deepl  # DeepL SDK
except ModuleNotFoundError:
    print("deepl package not installed. Install with 'pip install deepl'.", file=sys.stderr)
    sys.exit(1)

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Repo root detection
# ---------------------------------------------------------------------------

def detect_repo_root() -> Path:
    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        return Path(root)
    except Exception:
        return Path.cwd()


REPO_ROOT: Path = detect_repo_root()
SCRIPT_DIR: Path = Path(__file__).resolve().parent
README_PATH: Path = REPO_ROOT / "README.md"

# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Config:
    source_lang: str = "EN"
    languages: List[str] = field(default_factory=lambda: ["DE"])
    output_dir: Path = REPO_ROOT / "translations"
    template: str = "{basename}.{lang}{ext}"
    header_template_path: Path = REPO_ROOT / ".readme-i18n-header.md"
    marker_start: str = "<!-- readme-i18n start -->"
    marker_end: str = "<!-- readme-i18n end -->"

    @classmethod
    def load(cls) -> "Config":
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
# Flag‑Emoji mapping
# ---------------------------------------------------------------------------

FLAGS: Dict[str, str] = {}
for fp in (REPO_ROOT / "flags.json", SCRIPT_DIR.parent / "flags.json"):
    if fp.exists():
        try:
            data = json.load(fp.open())
            if isinstance(data, dict):
                FLAGS = {k.upper(): v for k, v in data.items()}
                break
        except Exception as exc:
            logging.warning("Failed to load %s: %s", fp, exc)

CREDIT_LINK = '<a href="https://github.com/Sprtacus/readme-i18n/">readme-i18n</a>'

# ---------------------------------------------------------------------------
# Segment‑Schutz (Code, Inline‑Code, Emoji)
# ---------------------------------------------------------------------------

EMOJI_PATTERN = (
    "[\U0001F600-\U0001F64F]"      # Emoticons (e.g., U+1F600 to U+1F64F)
    "|[\U0001F300-\U0001F5FF]"     # Miscellaneous Symbols and Pictographs
    "|[\U0001F680-\U0001F6FF]"     # Transport and Map Symbols
    "|[\U0001F1E6-\U0001F1FF]{2}"  # Regional Indicator Symbols (used for country flags)
    "|[\U00002600-\U000026FF]"     # Miscellaneous Symbols (e.g., weather, zodiac)
    "|[\U00002700-\U000027BF]"     # Dingbats (e.g., checkmarks, arrows)
    "|[\U0001F900-\U0001F9FF]"     # Supplemental Symbols and Pictographs (newer emoji range)
    "|[\U0001FA70-\U0001FAFF]"     # Symbols and Pictographs Extended-A (recent emoji additions)
    "|[\U00002500-\U00002BEF]"     # Box Drawing, Block Elements, and some CJK symbols
    "|[\U0001F018-\U0001F270]"     # Various older symbols and pictographs
    "|[\U0001F000-\U0001F02F]"     # Mahjong Tiles and Domino Tiles
)

EMOJI_MODIFIERS = "[\U0001F3FB-\U0001F3FF\U0000200D\U0000FE0F]"
FULL_EMOJI_PATTERN = rf"(?:{EMOJI_PATTERN})(?:{EMOJI_MODIFIERS})*"

EXCLUSION_PATTERN = re.compile(
    rf"""(
        ```[\s\S]*?```          # Fenced code-block
      | `[^`\n]+`               # Inline code
      | {FULL_EMOJI_PATTERN}    # Emojis (inkl. Modifier)
    )""",
    re.VERBOSE,
)

def protect_segments(text: str) -> Tuple[str, Dict[str, str]]:
    """Ersetzt alle auszuklammernden Segmente durch Platzhalter und liefert
    (gereinigter_text, mapping)."""
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
    for token, original in mapping.items():
        text = text.replace(token, original)
    return text

# ---------------------------------------------------------------------------
# Header helpers (unchanged)
# ---------------------------------------------------------------------------


def _load_header_template(cfg: Config) -> str:  # unchanged
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


def _relpath(target: Path, base: Path) -> str:  # unchanged
    return os.path.relpath(target, base).replace(os.sep, "/")


def _build_links(cfg: Config, cur_file: Path) -> str:  # unchanged
    base = cur_file.parent
    parts: List[str] = []

    def add(label: str, dest: Path, code: str):
        parts.append(f'<a href="{_relpath(dest, base)}">{FLAGS.get(code.upper(), '')} {label}</a>')

    add(cfg.source_lang, README_PATH, cfg.source_lang)
    for code in cfg.languages:
        fname = cfg.template.format(basename=README_PATH.stem, lang=code, ext=README_PATH.suffix)
        add(code, cfg.output_dir / fname, code)

    return " ·\n  ".join(parts)


def _translate(text: str, lang: str, tr: deepl.Translator | None) -> str:  # unchanged
    if lang == "EN" or tr is None:
        return text
    try:
        return tr.translate_text(text, target_lang=lang).text
    except Exception:
        return text


def _build_header(cfg: Config, file_: Path, lang: str, tr: deepl.Translator | None) -> str:  # unchanged
    tmpl = _load_header_template(cfg)
    return tmpl.format(
        links=_build_links(cfg, file_),
        languages_label=_translate("Languages:", lang, tr),
        credit=_translate(f"generated with {CREDIT_LINK} using DeepL", lang, tr),
    )


def _strip_header(text: str, cfg: Config) -> str:  # unchanged
    return re.sub(rf"{re.escape(cfg.marker_start)}[\s\S]*?{re.escape(cfg.marker_end)}\n?", "", text, flags=re.I).lstrip()


def ensure_header(path: Path, cfg: Config, lang: str, tr: deepl.Translator | None) -> bool:  # unchanged
    original = path.read_text("utf-8") if path.exists() else ""
    body = _strip_header(original, cfg)
    new_content = f"{_build_header(cfg, path, lang, tr)}\n\n{body}".rstrip() + "\n"
    if new_content != original:
        path.write_text(new_content, "utf-8")
        logging.info("Header updated in %s", path.relative_to(REPO_ROOT))
        return True
    return False

# ---------------------------------------------------------------------------
# Translation logic
# ---------------------------------------------------------------------------

def load_api_key() -> str | None:
    load_dotenv()
    return os.getenv("DEEPL_API_KEY")


def translate_body(txt: str, tr: deepl.Translator, lang: str) -> str | None:
    cleaned, mapping = protect_segments(txt)

    try:
        translated = cleaned if lang == "EN" else tr.translate_text(cleaned, target_lang=lang).text
    except deepl.DeepLException as exc:
        logging.error("Error translating to %s: %s", lang, exc)
        return None

    return restore_segments(translated, mapping)

def build_translations(readme: Path, key: str, cfg: Config) -> List[Path]:
    translator = deepl.Translator(key)
    source = _strip_header(readme.read_text("utf-8"), cfg)
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    created: List[Path] = []
    for lang in cfg.languages:
        text = translate_body(source, translator, lang)
        if text is None:
            continue
        fname = cfg.template.format(basename=readme.stem, lang=lang, ext=readme.suffix)
        target = cfg.output_dir / fname
        target.write_text(text, "utf-8")
        created.append(target)
        logging.info("Generated %s", target.relative_to(REPO_ROOT))
        ensure_header(target, cfg, lang, translator)
    return created

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Translate README via DeepL and maintain multilingual headers.")
    parser.add_argument("files", nargs="*", help="Paths from pre-commit (optional).")
    parser.add_argument("--check", action="store_true", help="Exit 1 if README.md is staged.")
    args = parser.parse_args(argv)

    logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
    if os.getenv("README_I18N_DEBUG"):
        logging.getLogger().setLevel(logging.DEBUG)

    cfg = Config.load()
    logging.info("source=%s, languages=%s", cfg.source_lang, cfg.languages)

    if ensure_header(README_PATH, cfg, cfg.source_lang, None):
        subprocess.run(["git", "add", str(README_PATH)], check=False)

    staged = args.files if args.files else subprocess.getoutput("git diff --cached --name-only").splitlines()
    if README_PATH.name not in staged:
        logging.info("README.md not staged; nothing to do.")
        return 0

    if args.check:
        return 1

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
    print("deepl package not installed. Install with 'pip install deepl'.", file=sys.stderr)
    sys.exit(1)

from __future__ import annotations

"""readme_i18n.py – translate README and keep a multilingual link‑header in **every** README.

Enhancements
------------
* **Header now bigger** (level‑2 heading) and includes a credit line:
  “Translations generated with *readme‑i18n*”.
* Still fully customisable via `.readme-i18n-header.md` – simply remove or edit the
  credit line if you prefer another wording.
"""

import argparse
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

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
README_PATH: Path = REPO_ROOT / "README.md"

# ---------------------------------------------------------------------------
# Configuration
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

        with pyproject.open("rb") as f:
            data = tomllib.load(f)
        cfg = data.get("tool", {}).get("readme-i18n", {})

        return cls(
            source_lang=cfg.get("source_lang", defaults.source_lang),
            languages=cfg.get("languages", defaults.languages),
            output_dir=REPO_ROOT / cfg.get("output_dir", defaults.output_dir.name),
            template=cfg.get("template", defaults.template),
            header_template_path=REPO_ROOT
            / cfg.get("header_template_path", defaults.header_template_path.name),
            marker_start=cfg.get("marker_start", defaults.marker_start),
            marker_end=cfg.get("marker_end", defaults.marker_end),
        )


# ---------------------------------------------------------------------------
# Header helpers
# ---------------------------------------------------------------------------


def _load_header_template(cfg: Config) -> str:
    if cfg.header_template_path.exists():
        template = cfg.header_template_path.read_text(encoding="utf-8")
    else:
        template = (
            "## Translations: {links}\n"
            "<sub>Translations generated with "
            "[readme‑i18n](https://github.com/Sprtacus/readme-i18n/)</sub>"
        )

    if "{links}" not in template:
        template += "\n{links}"

    if cfg.marker_start not in template:
        template = f"{cfg.marker_start}\n{template}"
    if cfg.marker_end not in template:
        template = f"{template}\n{cfg.marker_end}"

    return template


def _relpath(target: Path, base: Path) -> str:
    return os.path.relpath(target, base).replace(os.sep, "/")


def _build_links(cfg: Config, current_file: Path) -> str:
    cur_dir = current_file.parent

    def link(label: str, target: Path) -> str:
        return f"[{label}]({_relpath(target, cur_dir)})"

    links = [link(cfg.source_lang, README_PATH)]
    for code in cfg.languages:
        fname = cfg.template.format(basename=README_PATH.stem, lang=code, ext=README_PATH.suffix)
        links.append(link(code, cfg.output_dir / fname))
    return " | ".join(links)


def _build_header(cfg: Config, current_file: Path) -> str:
    return _load_header_template(cfg).format(links=_build_links(cfg, current_file))


def _strip_header(text: str, cfg: Config) -> str:
    pat = re.compile(rf"{re.escape(cfg.marker_start)}[\s\S]*?{re.escape(cfg.marker_end)}\n?", re.I)
    return re.sub(pat, "", text).lstrip()


def ensure_header(file_path: Path, cfg: Config) -> bool:
    original = file_path.read_text(encoding="utf-8") if file_path.exists() else ""
    body = _strip_header(original, cfg)
    new = f"{_build_header(cfg, file_path)}\n\n{body}".rstrip() + "\n"

    if new != original:
        file_path.write_text(new, encoding="utf-8")
        logging.info("Header updated in %s", file_path.relative_to(REPO_ROOT))
        return True
    return False


# ---------------------------------------------------------------------------
# Translation helpers
# ---------------------------------------------------------------------------


def load_api_key() -> str | None:
    load_dotenv()
    return os.getenv("DEEPL_API_KEY")


def translate_text(text: str, translator: deepl.Translator, lang: str) -> str | None:
    try:
        return translator.translate_text(text, target_lang=lang).text
    except deepl.DeepLException as exc:
        logging.error("Error translating to %s: %s", lang, exc)
        return None


def build_translations(readme: Path, api_key: str, cfg: Config) -> List[Path]:
    translator = deepl.Translator(api_key)
    src = _strip_header(readme.read_text(encoding="utf-8"), cfg)
    cfg.output_dir.mkdir(parents=True, exist_ok=True)

    generated: List[Path] = []
    for lang in cfg.languages:
        txt = translate_text(src, translator, lang)
        if txt is None:
            continue
        fname = cfg.template.format(basename=readme.stem, lang=lang, ext=readme.suffix)
        path = cfg.output_dir / fname
        path.write_text(txt, encoding="utf-8")
        generated.append(path)
        logging.info("Written %s", path.relative_to(REPO_ROOT))
        ensure_header(path, cfg)  # header for translation

    return generated


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Translate README via DeepL and maintain multilingual headers."
    )
    parser.add_argument("files", nargs="*", help="Paths from pre-commit (optional).")
    parser.add_argument("--check", action="store_true", help="Exit 1 if README.md is staged.")
    args = parser.parse_args(argv)

    logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)

    cfg = Config.load()
    logging.info("source=%s, languages=%s", cfg.source_lang, cfg.languages)

    if ensure_header(README_PATH, cfg):
        subprocess.run(["git", "add", str(README_PATH)], check=False)

    changed = args.files if args.files else subprocess.getoutput("git diff --cached --name-only").splitlines()
    if README_PATH.name not in changed:
        logging.info("README.md not staged; nothing to do.")
        return 0

    if args.check:
        return 1

    key = load_api_key()
    if not key:
        logging.warning("No DeepL API key found – skipping translation.")
        return 0

    generated = build_translations(README_PATH, key, cfg)
    if not generated:
        return 1

    subprocess.run(["git", "add", *map(str, generated)], check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())

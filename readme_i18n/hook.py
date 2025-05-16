import subprocess
import sys
import os
from dotenv import load_dotenv
import deepl

def load_api_key():
    load_dotenv()
    return os.getenv("DEEPL_API_KEY")

def translate_readme(api_key):
    with open("README.md", "r", encoding="utf-8") as f:
        source_text = f.read()

    translator = deepl.Translator(api_key)
    
    try:
        result = translator.translate_text(source_text, target_lang="EN-US")
    except deepl.DeepLException as e:
        print("Fehler bei der Übersetzung:", str(e))
        sys.exit(1)

    with open("README.en.md", "w", encoding="utf-8") as f:
        f.write(result.text)
    
    print("README.en.md wurde erfolgreich aktualisiert.")

def main():
    print("Checking for translation updates...")
    changed_files = subprocess.getoutput("git diff --name-only HEAD~1").splitlines()

    if "README.md" in changed_files:
        print("README.md wurde geändert. Übersetzungen werden aktualisiert...")

        api_key = load_api_key()
        if not api_key:
            print("Fehlender API Key. Bitte .env-Datei mit DEEPL_API_KEY einrichten.")
            sys.exit(1)

        translate_readme(api_key)

    return 0

if __name__ == "__main__":
    sys.exit(main())
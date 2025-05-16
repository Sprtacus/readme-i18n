import subprocess
import sys
import os
from dotenv import load_dotenv
import deepl

def load_api_key():
    load_dotenv()
    return os.getenv("DEEPL_API_KEY")

def translate_readme(api_key):
    readme_path = os.path.join(os.getcwd(), "README.md")
    target_path = os.path.join(os.getcwd(), "README.de.md")

    with open(readme_path, "r", encoding="utf-8") as f:
        source_text = f.read()

    translator = deepl.Translator(api_key)
    
    try:
        result = translator.translate_text(source_text, target_lang="DE")
    except deepl.DeepLException as e:
        print("Fehler bei der Übersetzung:", str(e))
        return False

    with open(target_path, "w", encoding="utf-8") as f:
        f.write(result.text)
    
    print("README.de.md wurde erfolgreich aktualisiert.")
    return True

def get_staged_files():
    output = subprocess.getoutput("git diff --cached --name-only")
    return output.splitlines()

def main():
    print("Checking for translation updates...", file=sys.stderr)

    changed_files = get_staged_files() 

    if "README.md" in changed_files:
        print("README.md wurde geändert. Übersetzungen werden aktualisiert...", file=sys.stderr)

        api_key = load_api_key()
        if not api_key:
            print("Warnung: Fehlender API Key. Bitte .env-Datei mit DEEPL_API_KEY einrichten.")
            return 0

        success = translate_readme(api_key)
        if not success:
            return 1
        
        subprocess.run(["git", "add", "README.de.md"])

    else:
        print("README.md wurde nicht geändert. Keine Übersetzung nötig.")

    return 0

if __name__ == "__main__":
    sys.exit(main())

def main():
    print("Checking for translation updates...")
    changed_files = subprocess.getoutput("git diff --name-only origin/HEAD").splitlines()
    if "README.md" in changed_files:
        print("README.md wurde geändert. Übersetzungen werden aktualisiert...")
        # z. B. update_translations()
        return 1  # Oder 0, wenn der Hook erfolgreich durchlaufen soll
    return 0

if __name__ == "__main__":
    main()
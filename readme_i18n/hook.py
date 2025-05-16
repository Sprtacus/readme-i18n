def main():
    print("Checking for translation updates...")

    # Hier prüfst du, ob sich z. B. README.md geändert hat
    # Wenn ja:
    confirm = input("README.md wurde geändert. Übersetzungen aktualisieren? [y/N]: ")
    if confirm.lower() == "y":
        print("Übersetzungen werden aktualisiert...")
        # update_translations()
    else:
        print("Überspringe Aktualisierung.")

if __name__ == "__main__":
    main()
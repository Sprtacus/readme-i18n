# readme-i18n

Automatically translate your `README.md` into multiple languages using the [DeepL API](https://www.deepl.com/docs-api/).  
Ideal for developers who want to keep multilingual documentation up to date – manually or automatically via Git hooks.
asdas
## ✨ Features

- Translates your `README.md` into any DeepL-supported language
- Generates and updates `README.xx.md` files (e.g. `README.de.md`, `README.fr.md`)
- Easy integration into any existing Git project
- `.env` support for secure API key handling
- Optional Git hook: auto-translate on every push
- MIT licensed – free for private and commercial use

## 📦 How to Integrate

Clone this repository into your project (e.g. under `tools/`):

```bash
git clone https://github.com/YOUR-USERNAME/readme-i18n.git tools/readme-i18n
```
or add it as a submodule:
```bash
git submodule add https://github.com/YOUR-USERNAME/readme-i18n.git tools/readme-i18n
```

## 🚀 Getting Started

### 1. Install dependencies
```bash
pip install -r tools/readme-i18n/requirements.txt
```
Requires Python 3.7 or newer.


### 2. Add your DeepL API key
Copy the example config:
```bash
cp tools/readme-i18n/.env.example tools/readme-i18n/.env
```
Then edit the .env file and set your API key:
```
DEEPL_API_KEY=your-api-key-here
```

### 3. Translate your README
From your project root, run:
```bash
python tools/readme-i18n/translator.py --lang de
```
This will generate or update a README.de.md file.

You can translate into multiple languages at once:
```bash
python tools/readme-i18n/translator.py --lang de fr es
```

## ⚙️ Optional: Auto-translate on Git push
Install the provided Git hook to keep translations in sync automatically:
```bash
bash tools/readme-i18n/install_git_hook.sh
```
This installs a pre-push hook that runs the translator with your chosen languages.

## 🛠 Configuration
You can configure the tool via CLI flags or environment variables.

## 📄 License

This project is licensed under the MIT License.

## ❤️ Credits

Created by developers for developers.
Feel free to fork, use, contribute or improve – pull requests welcome!

# readme-i18n

> ⚠️ **This project is in early development and maintained in my free time.** ⚠️  
> Expect breaking changes – contributions and ideas are always welcome!

Automatically translate your `README.md` into multiple languages using the [DeepL API](https://www.deepl.com/docs-api/).  
Ideal for developers who want to keep multilingual documentation up to date – manually or automatically via Git hooks.

## Features

- Translates your `README.md` into any DeepL-supported language
- Generates and updates `README.xx.md` files (e.g. `README.de.md`, `README.fr.md`)
- Easy integration into any existing Git project
- `.env` support for secure API key handling
- Optional Git hook: auto-translate on every push
- MIT licensed – free for private and commercial use

## How to Integrate

Clone this repository into your project (e.g. under `tools/`):

```bash
git clone https://github.com/YOUR-USERNAME/readme-i18n.git tools/readme-i18n
```
or add it as a submodule:
```bash
git submodule add https://github.com/YOUR-USERNAME/readme-i18n.git tools/readme-i18n
```

## License

This project is licensed under the MIT License.


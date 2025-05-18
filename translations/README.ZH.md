<!-- readme-i18n start -->
<p align="right">
  <strong>语言</strong> <a href="../README.md">🇬🇧 EN</a> ·
  <a href="README.DE.md">🇩🇪 DE</a> ·
  <a href="README.ZH.md">🇨🇳 ZH</a><br>
  <sub>使用 <a href="https://github.com/Sprtacus/readme-i18n/">readme-i18n</a> 生成，使用 DeepL</sub>
</p>
<!-- readme-i18n end -->

# readme-i18n

** 本项目处于早期开发阶段，由我利用业余时间维护。

使用 [DeepL API](https://www.deepl.com/docs-api/) 自动将您的 `README.md` 翻译成多种语言。  
非常适合希望保持多语言文档更新的开发人员--手动或通过 Git 钩子自动更新。

## ✨ 功能
广告
- 将您的 `README.md` 翻译成任何 DeepL 支持的语言
- 生成并更新 `README.xx.md` 文件（如 `README.de.md`, `README.fr.md`）
- 可轻松集成到任何现有的 Git 项目中
- 支持 `.env` 以安全处理 API 密钥
- 可选的 Git 钩子：每次推送时自动翻译
- MIT 许可--可免费用于私人和商业用途

## 📦 如何集成

将此版本库克隆到你的项目中（例如在 `tools/` 下）：

```bash
git clone https://github.com/Sprtacus/readme-i18n.git tools/readme-i18n
```
或将其添加为子模块：
```bash
git submodule add https://github.com/Sprtacus/readme-i18n.git tools/readme-i18n
```

## 📄 许可证

本项目采用 MIT 许可协议。

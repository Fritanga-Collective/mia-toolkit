# Translation catalogs

The GUI wraps every user-facing string in `_()` (see `mia/gui/i18n.py`). No
catalogs ship yet, so `gettext` falls back to English. Adding a language is
purely additive — no code change:

```bash
# 1. Extract translatable strings into a template:
xgettext -L Python -o mia/i18n/locale/mia.pot $(find mia/gui -name '*.py')

# 2. Create the Spanish (Mexico) catalog from the template:
mkdir -p mia/i18n/locale/es_MX/LC_MESSAGES
msginit -l es_MX -i mia/i18n/locale/mia.pot \
        -o mia/i18n/locale/es_MX/LC_MESSAGES/mia.po

# 3. Translate mia.po (msgstr lines), then compile to binary:
msgfmt mia/i18n/locale/es_MX/LC_MESSAGES/mia.po \
       -o mia/i18n/locale/es_MX/LC_MESSAGES/mia.mo
```

At runtime, `install(["es_MX"])` (or the OS default when called with no
argument) will pick up the compiled `.mo`.

# Translation catalogs

The GUI wraps every user-facing string in `_()`, and strings bound at import
time (class/module constants) in `N_()` (deferred — translated at use, so a
runtime language switch re-renders them).

Shipped languages: **English** (`en`), **Spanish** (`es`), and **Simplified
Chinese** (`zh`). Each has an editable `.po` (so translations are easy to update)
and a committed compiled `.mo`. English is also the source language, so its
catalog is an identity mapping. The in-app **Language** dropdown (top of the home
screen) switches at runtime and remembers the choice.

```
locale/
├── en/LC_MESSAGES/{mia.po, mia.mo}   # identity (source)
├── es/LC_MESSAGES/{mia.po, mia.mo}
└── zh/LC_MESSAGES/{mia.po, mia.mo}
    # .po: edit these   ·   .mo: compiled, loaded at runtime — must be committed
```

## Updating / adding a language

1. Re-extract strings (note both `-k_` and `-kN_`):

   ```bash
   xgettext --from-code=UTF-8 -L Python -k_ -kN_ \
     -o mia/i18n/locale/mia.pot $(find mia/gui -name '*.py')
   ```

2. Merge into an existing catalog (or `msginit` a new one):

   ```bash
   msgmerge --update mia/i18n/locale/es/LC_MESSAGES/mia.po mia/i18n/locale/mia.pot
   ```

3. Translate the `msgstr` lines, then compile:

   ```bash
   msgfmt mia/i18n/locale/es/LC_MESSAGES/mia.po \
     -o mia/i18n/locale/es/LC_MESSAGES/mia.mo
   ```

4. Register the language code + display name in `LANGUAGES` in `mia/gui/i18n.py`.

The PyInstaller specs bundle this whole `locale/` directory, so the compiled
`.mo` ships in the macOS/Windows builds.

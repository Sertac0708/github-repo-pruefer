"""Tests für die npx/uvx-Erkennung in scan.py.

Aufruf (ohne Abhängigkeiten, nur Standardbibliothek):
    python3 -m unittest discover -s tests -v

Hintergrund (12.10.2026, Prüfung von HKUDS/nanobot): Übersetzungstexte wie
„Node.js dengan npx diperlukan" oder „npx is required" wurden als Paketnamen
gelesen („diperlukan", „is") und im npm-Verzeichnis nachgeschlagen.
"""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SCAN = Path(__file__).resolve().parents[1] / "skills" / "repo-pruefer" / "scripts" / "scan.py"
spec = importlib.util.spec_from_file_location("scan", SCAN)
scan_mod = importlib.util.module_from_spec(spec)
sys.modules["scan"] = scan_mod
spec.loader.exec_module(scan_mod)


def scanne(dateien: dict[str, str]) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        wurzel = Path(tmp)
        for rel, inhalt in dateien.items():
            pfad = wurzel / rel
            pfad.parent.mkdir(parents=True, exist_ok=True)
            pfad.write_text(inhalt, encoding="utf-8")
        return scan_mod.scan(wurzel, None)


def fundstellen(erg: dict, titel_anfang: str) -> list[str]:
    """Orte (`datei:zeile`) aller Treffer einer Regel; Einträge haben die Form "`ort` — text"."""
    b = erg["befunde"]
    return sorted(eintrag.split("`")[1] for (_k, _s, titel), liste in b.treffer.items()
                  if titel.startswith(titel_anfang) for eintrag in liste)


class NpxErkennung(unittest.TestCase):

    def test_uebersetzungen_und_fliesstext_sind_keine_pakete(self):
        erg = scanne({
            "webui/src/i18n/locales/id/common.json":
                '{"marketplaceNpxRequired": "Node.js dengan npx diperlukan"}\n',
            "webui/src/i18n/locales/fr/common.json":
                '{"marketplaceNpxRequired": "Node.js avec npx est requis"}\n',
            "webui/src/i18n/locales/ja/common.json":
                '{"marketplaceNpxRequired": "npx を含む Node.js が必要です"}\n',
            "webui/src/i18n/locales/pt-BR/common.json":
                '{"marketplaceNpxRequired": "Node.js com npx é necessário"}\n',
            "webui/src/Settings.tsx":
                'const msg = t("marketplaceNpxRequired", { defaultValue: "Node.js with npx is required" });\n',
            "docs/faq.md": "You can use npx to run tools without installing them.\n",
            "docs/hinweis.md": "Hinweis: npx is required. Note: npx must be on PATH.\n",
            "docs/fehler.md": "When npx itself fails with ENOENT, npx ./src does not help.\n",
            "README.md": "```bash\n# npx without installing globally\n```\n",
        })
        self.assertEqual(erg["inventar"]["npx_pakete"], [])
        self.assertEqual(fundstellen(erg, "npx/uvx"), [])

    def test_echte_aufrufe_werden_weiter_erkannt(self):
        erg = scanne({
            "README.md": (
                "Install:\n\n```bash\nnpx -y @scope/werkzeug@1.2.0 init\n```\n\n"
                "Oder kurz: `npx clawhub@latest search`\n"
            ),
            "scripts/setup.sh": "#!/bin/sh\nset -e\ncd app && npx prettier --check .\n",
            "Dockerfile": "FROM node:22\nRUN npx playwright install\n",
            ".github/workflows/ci.yml": "steps:\n  - run: npx eslint .\n",
            "start.py": 'subprocess.run("uvx ruff check .", shell=True)\n',
            "docs/mcp.yml": "servers:\n  github:\n    command: npx -y @modelcontextprotocol/server-github\n",
            # npx als Argument eines anderen Befehls — die Schreibweise verrät den echten Aufruf
            "docs/codex.md": "codex mcp add sequential-thinking npx -y @modelcontextprotocol/server-sequential-thinking\n",
            "src/paths.ts": "// running inside WSL: wsl npx @modelcontextprotocol/server-filesystem /mnt/c/x\n",
            # aus nextlevelbuilder/ui-ux-pro-max-skill: Befehl in CSV-Zelle und in Kommentar
            "data/astro.csv": "Integrationen,Manuell,npx astro add tailwind,Hinweis\n",
            "scripts/requirements.txt": "#   npx shadcn-ui@latest init\n",
        })
        self.assertEqual(erg["inventar"]["npx_pakete"],
                         sorted({"@scope/werkzeug", "clawhub", "prettier", "playwright", "eslint",
                                 "@modelcontextprotocol/server-github",
                                 "@modelcontextprotocol/server-sequential-thinking",
                                 "@modelcontextprotocol/server-filesystem", "astro", "shadcn-ui"}))
        self.assertEqual(erg["inventar"]["uvx_pakete"], ["ruff"])

    def test_latest_regel_ignoriert_uebersetzungsdateien(self):
        erg = scanne({
            "locales/de.json": '{"hint": "Starte mit npx foo@latest"}\n',
            "install.sh": "npx bar@latest\n",
            # Fließtext aus modelcontextprotocol/servers — kein Aufruf
            "docs/run.md": ("Run it through uvx rather than the PyPI release.\n- uvx or pip (PyPI package)\n"
                            "Use when pointing npx, uvx or an MCP client at it.\n"),
        })
        self.assertEqual(fundstellen(erg, "Unversionierter"), ["install.sh:1"])


if __name__ == "__main__":
    unittest.main()

# mac-cleaner

Kommandozeilen-Tool für macOS zum Bereinigen von App-Resten, Analysieren grosser Dateien und Ausführen von Wartungsaufgaben — ähnlich wie CleanMyMac, aber offen und lokal.

## Installation

```bash
git clone https://github.com/m-ax-bsl/mac-cleaner.git
cd mac-cleaner
./install.sh
```

Das Script erstellt einen Symlink in `~/.local/bin` und trägt den Pfad bei Bedarf in `~/.zshrc` ein. Danach einmalig:

```bash
source ~/.zshrc
```

## Verwendung

```bash
mac-cleaner
```

## Funktionen

### Bereinigung
| Funktion | Beschreibung |
|---|---|
| App-Reste suchen | Findet Caches, Logs und Preferences von deinstallierten Apps |
| Grosse Dateien suchen | Listet alle Dateien über 100 MB sortiert nach Grösse |
| Papierkorb leeren | Zeigt Grösse und leert den Papierkorb nach Bestätigung |

### Leistung
| Funktion | Beschreibung |
|---|---|
| Login-Objekte anzeigen | Listet Login-Items und LaunchAgents |
| Entwickler-Cache bereinigen | Löscht Xcode DerivedData, CoreSimulator Caches, Swift PM Cache |
| Downloads analysieren | Zeigt Dateien nach Grösse und Alter, markiert Einträge über 90 Tage |

### Wartung
| Funktion | Beschreibung | sudo |
|---|---|---|
| DNS-Cache leeren | `dscacheutil` + `mDNSResponder` Neustart | ✓ |
| Spotlight neu indizieren | Löscht und rebuilt den Spotlight-Index | ✓ |
| macOS-Wartungsskripte | `periodic daily weekly monthly` (macOS 14 und älter) | ✓ |

## Sicherheit

- Caches und Logs werden nur nach Bestätigung gelöscht
- `Application Support` und `Preferences` werden nur angezeigt, nie automatisch gelöscht
- System-Dateien (`com.apple.*` etc.) werden übersprungen
- Alle sudo-Befehle verwenden absolute Pfade

## Voraussetzungen

- macOS
- Python 3

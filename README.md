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
| Homebrew-Cache bereinigen | Zeigt und löscht alte Homebrew-Pakete (`brew cleanup`) |
| Browser-Caches bereinigen | Safari, Chrome, Firefox, Arc, Brave, Edge u.a. |
| iOS-Backups anzeigen | Zeigt Grösse und Datum aller iPhone/iPad-Backups |
| Gespeicherte App-Zustände | Löscht Fenster-Snapshots aus `~/Library/Saved Application State` |
| Paketmanager-Caches bereinigen | npm, pip, yarn, gem, Cargo, Maven, Gradle u.a. |

### Leistung
| Funktion | Beschreibung |
|---|---|
| Login-Objekte anzeigen | Listet Login-Items und LaunchAgents |
| Defekte LaunchAgents entfernen | Findet und löscht LaunchAgents mit fehlenden Programmen |
| Entwickler-Cache bereinigen | Löscht Xcode DerivedData, CoreSimulator Caches, Swift PM Cache |
| Downloads analysieren | Zeigt Dateien nach Grösse und Alter, markiert Einträge über 90 Tage |
| Festplattennutzung anzeigen | Übersicht der grössten Ordner im Home-Verzeichnis mit Balkendiagramm |
| App deinstallieren | Findet alle Dateien einer App in Library-Ordnern und löscht sie |
| Alte Dateien suchen | Listet Dateien, die seit über einem Jahr nicht verändert wurden |
| Mail-Ordner analysieren | Zeigt Grösse des Mail-Stores aufgeteilt nach Accounts |

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

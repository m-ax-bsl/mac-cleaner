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
| Temporäre Dateien bereinigen | `/private/tmp` (eigene Dateien), TemporaryItems, CloudKit-Cache |
| App Store Cache bereinigen | App Store Download- und StoreKit-Caches löschen |
| Crash Reports löschen | Entfernt `.crash`-Dateien aus `~/Library/Logs/DiagnosticReports` |
| Installer-Dateien suchen | Findet `.dmg`, `.pkg`, `.iso`-Dateien im Home-Verzeichnis |
| Virtuelle Maschinen suchen | Findet `.vmwarevm`, `.pvm`, `.vhd`, `.vmdk`-Dateien |
| Archive suchen | Findet `.zip`, `.tar.gz`, `.rar`-Dateien, markiert Einträge über 6 Monate |
| User-Caches analysieren | Zeigt `~/Library/Caches` nach Grösse, löscht Cache von nicht installierten Apps |
| Log-Dateien bereinigen | Zeigt `~/Library/Logs` nach Grösse und Alter, löscht nach Bestätigung |
| Screenshots aufräumen | Findet Screenshots auf Desktop/Downloads/Documents/Pictures |
| Docker bereinigen | `docker system prune` wenn Docker installiert und gestartet ist |

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
| Duplikate suchen | Findet identische Dateien via Grösse + MD5-Hash |
| Leere Ordner finden | Sucht und löscht leere Verzeichnisse im Home-Ordner |
| Mail-Anhänge analysieren | Zeigt Grösse und Typ aller heruntergeladenen Mail-Anhänge |
| Time Machine Snapshots | Listet lokale Time Machine Snapshots, optional löschen |
| Schriften analysieren | Zeigt installierte Fonts nach Quelle, markiert Duplikate |
| iCloud Drive analysieren | Zeigt Belegung von iCloud Drive nach Ordner mit Balkendiagramm |

### Wartung
| Funktion | Beschreibung | sudo |
|---|---|---|
| DNS-Cache leeren | `dscacheutil` + `mDNSResponder` Neustart | ✓ |
| Spotlight neu indizieren | Löscht und rebuilt den Spotlight-Index | ✓ |
| macOS-Wartungsaufgaben | LaunchServices-Datenbank neu aufbauen, Schriften-Cache bereinigen | ✓ |
| System-Informationen | CPU, RAM, Akku, Uptime, Festplattennutzung | |
| Sprachdateien bereinigen | Entfernt ungenutzte `.lproj`-Ordner aus App-Bundles | |
| RAM freigeben | Leert den inaktiven RAM-Cache via `purge` | ✓ |
| Datenschutz-Caches | QuickLook-Vorschau, Recents-Listen, Notification-Cache | |
| Netzwerk-Informationen | IP, WiFi SSID, DNS-Server, Gateway, TCP-Verbindungen | |
| Browser-Erweiterungen | Listet installierte Erweiterungen in Chrome, Brave, Edge, Safari | |
| System-Erweiterungen | Zeigt Kernel Extensions und System Extensions | |

## Sicherheit

- Caches und Logs werden nur nach Bestätigung gelöscht
- `Application Support` und `Preferences` werden nur angezeigt, nie automatisch gelöscht
- System-Dateien (`com.apple.*` etc.) werden übersprungen
- Alle sudo-Befehle verwenden absolute Pfade

## Voraussetzungen

- macOS
- Python 3

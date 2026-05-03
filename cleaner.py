#!/usr/bin/env python3
"""mac-cleaner — findet App-Reste, grosse Dateien und fuehrt Wartungsaufgaben aus"""

import os
import shutil
import subprocess
import glob
import plistlib
import hashlib
from datetime import datetime

HOME = os.path.expanduser("~")

# Caches und Logs sind sicher: werden automatisch neu erstellt
SICHERE_ORTE = [
    "~/Library/Caches",
    "~/Library/Logs",
]

# Application Support und Preferences könnten Benutzerdaten enthalten
VORSICHT_ORTE = [
    "~/Library/Application Support",
    "~/Library/Preferences",
]

# Containers und Group Containers werden bewusst weggelassen — zu riskant

SYSTEM_PRAEFIXE = [
    "com.apple.", "com.osxfuse.", "com.openssh.",
    "apple", "safari", "finder", "dock", "spotlight",
    "loginwindow", "systempreferences", "facetime",
    "icloud", "itunes", "music", "photos", "mail",
]

def bytes_lesbar(b):
    for einheit in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {einheit}"
        b /= 1024
    return f"{b:.1f} TB"

def installierte_apps():
    apps = set()
    for ordner in ["/Applications", os.path.join(HOME, "Applications")]:
        if os.path.exists(ordner):
            for name in os.listdir(ordner):
                if name.endswith(".app"):
                    apps.add(name.replace(".app", "").lower())
    return apps

def ist_systemdatei(name):
    name_lower = name.lower()
    return any(name_lower.startswith(p.lower()) for p in SYSTEM_PRAEFIXE)

def ordner_groesse(pfad):
    try:
        if os.path.isdir(pfad):
            return sum(
                os.path.getsize(os.path.join(w, f))
                for w, _, fs in os.walk(pfad)
                for f in fs
                if not os.path.islink(os.path.join(w, f))
            )
        return os.path.getsize(pfad)
    except (OSError, PermissionError):
        return 0

def ist_app_rest(eintrag, installierte):
    eintrag_lower = eintrag.lower()
    return not any(
        app in eintrag_lower or eintrag_lower in app
        for app in installierte
    )

# ── BEREINIGUNG ───────────────────────────────────────────────────────────────

def app_reste_suchen():
    print("\nSuche App-Reste ...\n")
    apps = installierte_apps()

    # SICHER: Caches und Logs von nicht installierten Apps
    sichere_reste = []
    for ort in SICHERE_ORTE:
        pfad = os.path.expanduser(ort)
        if not os.path.exists(pfad):
            continue
        try:
            for eintrag in os.listdir(pfad):
                if ist_systemdatei(eintrag):
                    continue
                if ist_app_rest(eintrag, apps):
                    voller_pfad = os.path.join(pfad, eintrag)
                    groesse = ordner_groesse(voller_pfad)
                    kurz = voller_pfad.replace(HOME, "~")
                    sichere_reste.append((groesse, kurz, voller_pfad))
        except PermissionError:
            pass

    if sichere_reste:
        sichere_reste.sort(reverse=True)
        total = sum(g for g, _, _ in sichere_reste)
        print("  SICHER ZU LOESCHEN (Caches & Logs von deinstallierten Apps)")
        print(f"  {'Groesse':<12} Pfad")
        print(f"  {'-'*60}")
        for groesse, kurz, _ in sichere_reste:
            print(f"  {bytes_lesbar(groesse):<12} {kurz}")
        print(f"\n  Total: {bytes_lesbar(total)} in {len(sichere_reste)} Eintraegen")

        antwort = input("\n  Alle sicheren Reste loeschen? (j/n): ").strip().lower()
        if antwort == "j":
            for _, _, pfad in sichere_reste:
                try:
                    if os.path.isdir(pfad):
                        shutil.rmtree(pfad)
                    else:
                        os.remove(pfad)
                    print(f"  Geloescht: {pfad.replace(HOME, '~')}")
                except Exception as e:
                    print(f"  Fehler bei {pfad.replace(HOME, '~')}: {e}")
            print(f"\n  {bytes_lesbar(total)} freigegeben.")
        else:
            print("  Nichts geloescht.")
    else:
        print("  Keine sicheren App-Reste gefunden.")

    # ZUR KONTROLLE: Application Support und Preferences
    vorsicht_reste = []
    for ort in VORSICHT_ORTE:
        pfad = os.path.expanduser(ort)
        if not os.path.exists(pfad):
            continue
        try:
            for eintrag in os.listdir(pfad):
                if ist_systemdatei(eintrag):
                    continue
                if ist_app_rest(eintrag, apps):
                    voller_pfad = os.path.join(pfad, eintrag)
                    groesse = ordner_groesse(voller_pfad)
                    kurz = voller_pfad.replace(HOME, "~")
                    vorsicht_reste.append((groesse, kurz, voller_pfad))
        except PermissionError:
            pass

    if vorsicht_reste:
        vorsicht_reste.sort(reverse=True)
        total = sum(g for g, _, _ in vorsicht_reste)
        print(f"\n  ZUR KONTROLLE (koennen Benutzerdaten enthalten — bitte selbst pruefen)")
        print(f"  {'Groesse':<12} Pfad")
        print(f"  {'-'*60}")
        for groesse, kurz, _ in vorsicht_reste:
            print(f"  {bytes_lesbar(groesse):<12} {kurz}")
        print(f"\n  Total: {bytes_lesbar(total)} — nicht automatisch geloescht.")

def grosse_dateien_suchen(min_mb=100):
    print(f"\nSuche Dateien groesser als {min_mb} MB ...\n")
    gefunden = []
    min_bytes = min_mb * 1024 * 1024

    for wurzel, ordner, dateien in os.walk(HOME):
        ordner[:] = [o for o in ordner if not o.startswith('.')
                     and o not in ["Library", "Applications"]]
        for datei in dateien:
            try:
                voller_pfad = os.path.join(wurzel, datei)
                groesse = os.path.getsize(voller_pfad)
                if groesse >= min_bytes:
                    gefunden.append((groesse, voller_pfad))
            except (OSError, PermissionError):
                pass

    gefunden.sort(reverse=True)

    if not gefunden:
        print("  Keine grossen Dateien gefunden.")
        return

    print(f"  {'Groesse':<12} Datei")
    print(f"  {'-'*60}")
    for groesse, pfad in gefunden[:20]:
        print(f"  {bytes_lesbar(groesse):<12} {pfad.replace(HOME, '~')}")

    print(f"\n  {len(gefunden)} Dateien gefunden (zeige max. 20)")

def brew_cache_bereinigen():
    print("\nHomebrew-Cache bereinigen ...\n")
    brew = shutil.which("brew")
    if not brew:
        print("  Homebrew nicht installiert.")
        return

    ergebnis = subprocess.run([brew, "cleanup", "--dry-run"], capture_output=True, text=True)
    zeilen = [z for z in ergebnis.stdout.splitlines() if z.strip() and not z.startswith("==>")]
    if not zeilen:
        print("  Homebrew-Cache ist bereits leer.")
        return

    print(f"  {len(zeilen)} Eintraege gefunden:\n")
    for z in zeilen[:20]:
        print(f"    {z.strip()}")
    if len(zeilen) > 20:
        print(f"    ... ({len(zeilen) - 20} weitere)")

    antwort = input("\n  Homebrew-Cache jetzt leeren? (j/n): ").strip().lower()
    if antwort == "j":
        subprocess.run([brew, "cleanup"], capture_output=False)
        print("  Homebrew-Cache geleert.")
    else:
        print("  Nichts geloescht.")

def browser_cache_bereinigen():
    print("\nBrowser-Caches bereinigen ...\n")

    browser_caches = [
        ("Safari",   "~/Library/Caches/com.apple.Safari"),
        ("Chrome",   "~/Library/Caches/Google/Chrome"),
        ("Firefox",  "~/Library/Caches/Firefox"),
        ("Arc",      "~/Library/Caches/Arc"),
        ("Brave",    "~/Library/Caches/BraveSoftware"),
        ("Edge",     "~/Library/Caches/Microsoft Edge"),
        ("Opera",    "~/Library/Caches/com.operasoftware.Opera"),
        ("Vivaldi",  "~/Library/Caches/Vivaldi"),
        ("Chromium", "~/Library/Caches/Chromium"),
    ]

    gefunden = []
    for browser, pfad_tmpl in browser_caches:
        pfad = os.path.expanduser(pfad_tmpl)
        if os.path.exists(pfad):
            groesse = ordner_groesse(pfad)
            gefunden.append((browser, groesse, pfad))

    if not gefunden:
        print("  Keine Browser-Caches gefunden.")
        return

    total = sum(g for _, g, _ in gefunden)
    print(f"  {'Browser':<12} Groesse")
    print(f"  {'-'*40}")
    for browser, groesse, _ in gefunden:
        print(f"  {browser:<12} {bytes_lesbar(groesse)}")
    print(f"\n  Total: {bytes_lesbar(total)}")

    antwort = input("\n  Alle Browser-Caches loeschen? (j/n): ").strip().lower()
    if antwort == "j":
        for browser, groesse, pfad in gefunden:
            try:
                shutil.rmtree(pfad)
                print(f"  Geloescht: {browser} ({bytes_lesbar(groesse)})")
            except Exception as e:
                print(f"  Fehler bei {browser}: {e}")
        print(f"\n  {bytes_lesbar(total)} freigegeben.")
    else:
        print("  Nichts geloescht.")

def ios_backups_anzeigen():
    print("\niOS-Backups analysieren ...\n")
    backup_pfad = os.path.expanduser("~/Library/Application Support/MobileSync/Backup")
    if not os.path.exists(backup_pfad):
        print("  Keine iOS-Backups gefunden.")
        return

    backups = [d for d in os.listdir(backup_pfad)
               if os.path.isdir(os.path.join(backup_pfad, d))]
    if not backups:
        print("  Keine iOS-Backups gefunden.")
        return

    total = 0
    print(f"  {'Groesse':<12} {'Datum':<14} Backup-ID")
    print(f"  {'-'*60}")
    for backup_id in sorted(backups):
        pfad = os.path.join(backup_pfad, backup_id)
        groesse = ordner_groesse(pfad)
        total += groesse
        mtime = os.path.getmtime(pfad)
        datum = datetime.fromtimestamp(mtime).strftime("%d.%m.%Y")

        # Gerätename aus Info.plist lesen falls vorhanden
        info_plist = os.path.join(pfad, "Info.plist")
        geraet = backup_id[:8]
        if os.path.exists(info_plist):
            try:
                with open(info_plist, "rb") as f:
                    info = plistlib.load(f)
                geraet = info.get("Device Name", geraet)
            except Exception:
                pass

        print(f"  {bytes_lesbar(groesse):<12} {datum:<14} {geraet}")

    print(f"\n  Total: {bytes_lesbar(total)} in {len(backups)} Backup(s)")
    print("  Tipp: Alte Backups loeschen in Finder > Mac-Name > Verwalten.")

def papierkorb_leeren():
    print("\nPapierkorb wird analysiert ...\n")
    trash = os.path.join(HOME, ".Trash")
    if not os.path.exists(trash):
        print("  Papierkorb ist bereits leer.")
        return

    eintraege = os.listdir(trash)
    if not eintraege:
        print("  Papierkorb ist bereits leer.")
        return

    total = ordner_groesse(trash)
    print(f"  {len(eintraege)} Eintraege im Papierkorb ({bytes_lesbar(total)})")

    antwort = input("\n  Papierkorb jetzt leeren? (j/n): ").strip().lower()
    if antwort == "j":
        for eintrag in eintraege:
            pfad = os.path.join(trash, eintrag)
            try:
                if os.path.isdir(pfad):
                    shutil.rmtree(pfad)
                else:
                    os.remove(pfad)
            except Exception as e:
                print(f"  Fehler: {e}")
        print(f"  Papierkorb geleert — {bytes_lesbar(total)} freigegeben.")
    else:
        print("  Nichts geloescht.")

# ── LEISTUNG ──────────────────────────────────────────────────────────────────

def defekte_launch_agenten_entfernen():
    print("\nDefekte LaunchAgents suchen ...\n")
    agents_pfad = os.path.join(HOME, "Library", "LaunchAgents")
    if not os.path.exists(agents_pfad):
        print("  Keine LaunchAgents gefunden.")
        return

    defekte = []
    for datei in sorted(os.listdir(agents_pfad)):
        if not datei.endswith(".plist"):
            continue
        pfad = os.path.join(agents_pfad, datei)
        try:
            with open(pfad, "rb") as f:
                plist = plistlib.load(f)
            programm = None
            if "Program" in plist:
                programm = plist["Program"]
            elif "ProgramArguments" in plist:
                args = plist["ProgramArguments"]
                if args:
                    programm = args[0]
            if programm and not os.path.exists(programm):
                defekte.append((datei, pfad, programm))
        except Exception:
            pass

    if not defekte:
        print("  Alle LaunchAgents sind in Ordnung.")
        return

    print(f"  {len(defekte)} defekte LaunchAgents gefunden:\n")
    for datei, _, programm in defekte:
        print(f"  • {datei}")
        print(f"    Programm fehlt: {programm}")

    antwort = input("\n  Defekte LaunchAgents loeschen? (j/n): ").strip().lower()
    if antwort == "j":
        for datei, pfad, _ in defekte:
            try:
                os.remove(pfad)
                print(f"  Geloescht: {datei}")
            except Exception as e:
                print(f"  Fehler bei {datei}: {e}")
    else:
        print("  Nichts geloescht.")

def login_objekte_anzeigen():
    print("\nLogin-Objekte (starten beim Anmelden) ...\n")

    # Klassische Login-Items per AppleScript
    ergebnis = subprocess.run(
        ["osascript", "-e",
         'tell application "System Events" to get the name of every login item'],
        capture_output=True, text=True
    )
    if ergebnis.returncode == 0 and ergebnis.stdout.strip():
        items = [i.strip() for i in ergebnis.stdout.strip().split(",") if i.strip()]
        print("  Login-Items (Systemeinstellungen):")
        for item in items:
            print(f"    • {item}")
    else:
        print("  Login-Items: (keine oder kein Zugriff)")

    # LaunchAgents des Benutzers
    agents_pfad = os.path.join(HOME, "Library", "LaunchAgents")
    if os.path.exists(agents_pfad):
        agents = [f for f in os.listdir(agents_pfad) if f.endswith(".plist")]
        if agents:
            print(f"\n  LaunchAgents (~{agents_pfad.replace(HOME, '~')}):")
            for a in sorted(agents):
                print(f"    • {a}")

    # System-LaunchAgents (kein Loeschen, nur anzeigen)
    sys_agents = "/Library/LaunchAgents"
    if os.path.exists(sys_agents):
        try:
            agents = [f for f in os.listdir(sys_agents) if f.endswith(".plist")]
            if agents:
                print(f"\n  System-LaunchAgents ({sys_agents}):")
                for a in sorted(agents):
                    print(f"    • {a}")
        except PermissionError:
            pass

    print("\n  Tipp: Unbekannte Login-Items kannst du in den")
    print("  Systemeinstellungen > Allgemein > Anmeldeobjekte deaktivieren.")

def entwickler_cache_bereinigen():
    print("\nEntwickler-Cache analysieren ...\n")

    kandidaten = [
        ("Xcode DerivedData",      "~/Library/Developer/Xcode/DerivedData",        True),
        ("Xcode Device Support",   "~/Library/Developer/Xcode/iOS DeviceSupport",   False),
        ("watchOS Device Support", "~/Library/Developer/Xcode/watchOS DeviceSupport", False),
        ("CoreSimulator Caches",   "~/Library/Developer/CoreSimulator/Caches",       True),
        ("Swift PM Cache",         "~/Library/org.swift.swiftpm",                    True),
    ]

    loeschbar = []
    for label, pfad_tmpl, sicher in kandidaten:
        pfad = os.path.expanduser(pfad_tmpl)
        if not os.path.exists(pfad):
            continue
        groesse = ordner_groesse(pfad)
        kurz = pfad.replace(HOME, "~")
        marker = "SICHER" if sicher else "MANUELL PRUEFEN"
        print(f"  [{marker}] {bytes_lesbar(groesse):<10} {kurz}")
        if sicher:
            loeschbar.append((groesse, pfad, label))

    if not loeschbar:
        print("  Keine Entwickler-Caches gefunden.")
        return

    total = sum(g for g, _, _ in loeschbar)
    print(f"\n  Sicher loeschbar: {bytes_lesbar(total)}")

    antwort = input("\n  Alle sicheren Entwickler-Caches loeschen? (j/n): ").strip().lower()
    if antwort == "j":
        for groesse, pfad, label in loeschbar:
            try:
                shutil.rmtree(pfad)
                print(f"  Geloescht: {label} ({bytes_lesbar(groesse)})")
            except Exception as e:
                print(f"  Fehler bei {label}: {e}")
        print(f"\n  {bytes_lesbar(total)} freigegeben.")
    else:
        print("  Nichts geloescht.")

def downloads_analysieren():
    print("\nDownloads-Ordner analysieren ...\n")
    downloads = os.path.join(HOME, "Downloads")
    if not os.path.exists(downloads):
        print("  Downloads-Ordner nicht gefunden.")
        return

    dateien = []
    for name in os.listdir(downloads):
        pfad = os.path.join(downloads, name)
        try:
            groesse = ordner_groesse(pfad)
            mtime = os.path.getmtime(pfad)
            alter_tage = (datetime.now().timestamp() - mtime) / 86400
            dateien.append((groesse, alter_tage, name, pfad))
        except (OSError, PermissionError):
            pass

    if not dateien:
        print("  Downloads-Ordner ist leer.")
        return

    dateien.sort(reverse=True)
    total = sum(g for g, _, _, _ in dateien)
    print(f"  {len(dateien)} Eintraege, {bytes_lesbar(total)} gesamt\n")
    print(f"  {'Groesse':<12} {'Alter':<12} Name")
    print(f"  {'-'*60}")
    for groesse, tage, name, _ in dateien[:25]:
        alter_str = f"{int(tage)}d" if tage < 365 else f"{tage/365:.1f}y"
        print(f"  {bytes_lesbar(groesse):<12} {alter_str:<12} {name}")

    if len(dateien) > 25:
        print(f"  ... ({len(dateien) - 25} weitere nicht angezeigt)")

    # Alte Eintraege (> 90 Tage) hervorheben
    alte = [(g, t, n, p) for g, t, n, p in dateien if t > 90]
    if alte:
        alte_total = sum(g for g, _, _, _ in alte)
        print(f"\n  {len(alte)} Eintraege aelter als 90 Tage ({bytes_lesbar(alte_total)})")
        print("  Tipp: Oeffne den Downloads-Ordner und loesche manuell was du nicht mehr brauchst.")

def gespeicherte_zustaende_bereinigen():
    print("\nGespeicherte App-Zustaende bereinigen ...\n")
    pfad = os.path.join(HOME, "Library", "Saved Application State")
    if not os.path.exists(pfad):
        print("  Keine gespeicherten Zustaende gefunden.")
        return

    eintraege = [d for d in os.listdir(pfad) if os.path.isdir(os.path.join(pfad, d))]
    if not eintraege:
        print("  Keine gespeicherten Zustaende gefunden.")
        return

    total = ordner_groesse(pfad)
    print(f"  {len(eintraege)} gespeicherte App-Zustaende ({bytes_lesbar(total)})\n")
    for name in sorted(eintraege)[:15]:
        groesse = ordner_groesse(os.path.join(pfad, name))
        print(f"  {bytes_lesbar(groesse):<12} {name}")
    if len(eintraege) > 15:
        print(f"  ... ({len(eintraege) - 15} weitere)")

    print("\n  Diese Dateien speichern offene Fenster beim Beenden.")
    print("  macOS erstellt sie automatisch neu — sicher zu loeschen.")
    antwort = input("\n  Alle gespeicherten Zustaende loeschen? (j/n): ").strip().lower()
    if antwort == "j":
        try:
            shutil.rmtree(pfad)
            os.makedirs(pfad)
            print(f"  Geloescht — {bytes_lesbar(total)} freigegeben.")
        except Exception as e:
            print(f"  Fehler: {e}")
    else:
        print("  Nichts geloescht.")

def festplattennutzung_anzeigen():
    print("\nFestplattennutzung analysieren ...\n")

    # Gesamte Disk-Nutzung
    disk = shutil.disk_usage("/")
    print(f"  Festplatte gesamt: {bytes_lesbar(disk.total)}")
    print(f"  Belegt:            {bytes_lesbar(disk.used)} ({disk.used/disk.total*100:.0f}%)")
    print(f"  Frei:              {bytes_lesbar(disk.free)}\n")

    # Top-Ordner im Home-Verzeichnis
    print(f"  Groesste Ordner in ~:\n")
    ordner = []
    skip = {"Library"}
    try:
        for name in os.listdir(HOME):
            if name.startswith(".") or name in skip:
                continue
            pfad = os.path.join(HOME, name)
            groesse = ordner_groesse(pfad)
            ordner.append((groesse, name))
    except PermissionError:
        pass

    # Library separat mit du fuer korrekte Groesse
    lib_pfad = os.path.join(HOME, "Library")
    try:
        ergebnis = subprocess.run(
            ["du", "-sk", lib_pfad], capture_output=True, text=True
        )
        if ergebnis.returncode == 0:
            kb = int(ergebnis.stdout.split()[0])
            ordner.append((kb * 1024, "Library"))
    except Exception:
        pass

    ordner.sort(reverse=True)
    balken_max = ordner[0][0] if ordner else 1
    print(f"  {'Groesse':<12} {'':30} Ordner")
    print(f"  {'-'*60}")
    for groesse, name in ordner[:15]:
        balken = int(groesse / balken_max * 20)
        print(f"  {bytes_lesbar(groesse):<12} {'█' * balken:<20} {name}")

def app_deinstallieren():
    print("\nApp deinstallieren ...\n")
    app_name = input("  App-Name eingeben (z.B. Spotify): ").strip()
    if not app_name:
        return

    app_lower = app_name.lower()
    print(f"\n  Suche Dateien fuer '{app_name}' ...\n")

    suchpfade = [
        f"/Applications/{app_name}.app",
        os.path.join(HOME, f"Applications/{app_name}.app"),
        os.path.join(HOME, f"Library/Application Support/{app_name}"),
        os.path.join(HOME, f"Library/Caches/{app_name}"),
        os.path.join(HOME, f"Library/Logs/{app_name}"),
        os.path.join(HOME, f"Library/Preferences/{app_name}.plist"),
    ]

    # Wildcard-Suche in typischen Ordnern
    wildcard_orte = [
        os.path.join(HOME, "Library/Application Support"),
        os.path.join(HOME, "Library/Caches"),
        os.path.join(HOME, "Library/Logs"),
        os.path.join(HOME, "Library/Preferences"),
        os.path.join(HOME, "Library/Containers"),
        os.path.join(HOME, "Library/Group Containers"),
        os.path.join(HOME, "Library/LaunchAgents"),
    ]
    for ort in wildcard_orte:
        if not os.path.exists(ort):
            continue
        try:
            for eintrag in os.listdir(ort):
                if app_lower in eintrag.lower():
                    suchpfade.append(os.path.join(ort, eintrag))
        except PermissionError:
            pass

    gefunden = []
    gesehen = set()
    for pfad in suchpfade:
        if pfad in gesehen or not os.path.exists(pfad):
            continue
        gesehen.add(pfad)
        groesse = ordner_groesse(pfad)
        gefunden.append((groesse, pfad))

    if not gefunden:
        print(f"  Keine Dateien fuer '{app_name}' gefunden.")
        return

    gefunden.sort(reverse=True)
    total = sum(g for g, _ in gefunden)
    print(f"  {'Groesse':<12} Pfad")
    print(f"  {'-'*60}")
    for groesse, pfad in gefunden:
        print(f"  {bytes_lesbar(groesse):<12} {pfad.replace(HOME, '~')}")
    print(f"\n  Total: {bytes_lesbar(total)} in {len(gefunden)} Eintraegen")

    antwort = input("\n  Alle gefundenen Dateien loeschen? (j/n): ").strip().lower()
    if antwort == "j":
        for _, pfad in gefunden:
            try:
                if os.path.isdir(pfad):
                    shutil.rmtree(pfad)
                else:
                    os.remove(pfad)
                print(f"  Geloescht: {pfad.replace(HOME, '~')}")
            except Exception as e:
                print(f"  Fehler: {e}")
        print(f"\n  {bytes_lesbar(total)} freigegeben.")
    else:
        print("  Nichts geloescht.")

def paketmanager_cache_bereinigen():
    print("\nPaketmanager-Caches analysieren ...\n")

    kandidaten = [
        ("npm",      "~/.npm/_cacache"),
        ("yarn",     "~/.yarn/cache"),
        ("pip",      "~/Library/Caches/pip"),
        ("gem",      "~/.gem/ruby"),
        ("Composer", "~/.composer/cache"),
        ("Cargo",    "~/.cargo/registry/cache"),
        ("Maven",    "~/.m2/repository"),
        ("Gradle",   "~/.gradle/caches"),
        ("Pub",      "~/.pub-cache"),
    ]

    loeschbar = []
    for label, pfad_tmpl in kandidaten:
        pfad = os.path.expanduser(pfad_tmpl)
        if not os.path.exists(pfad):
            continue
        groesse = ordner_groesse(pfad)
        kurz = pfad.replace(HOME, "~")
        print(f"  {label:<12} {bytes_lesbar(groesse):<12} {kurz}")
        loeschbar.append((label, groesse, pfad))

    if not loeschbar:
        print("  Keine Paketmanager-Caches gefunden.")
        return

    total = sum(g for _, g, _ in loeschbar)
    print(f"\n  Total: {bytes_lesbar(total)}")

    antwort = input("\n  Alle Paketmanager-Caches loeschen? (j/n): ").strip().lower()
    if antwort == "j":
        for label, groesse, pfad in loeschbar:
            try:
                shutil.rmtree(pfad)
                print(f"  Geloescht: {label} ({bytes_lesbar(groesse)})")
            except Exception as e:
                print(f"  Fehler bei {label}: {e}")
        print(f"\n  {bytes_lesbar(total)} freigegeben.")
    else:
        print("  Nichts geloescht.")

def alte_dateien_suchen(min_tage=365):
    print(f"\nDateien suchen die seit mehr als {min_tage} Tagen nicht veraendert wurden ...\n")
    grenze = datetime.now().timestamp() - min_tage * 86400
    gefunden = []

    for wurzel, ordner, dateien in os.walk(HOME):
        ordner[:] = [o for o in ordner if not o.startswith(".")
                     and o not in ["Library", "Applications"]]
        for datei in dateien:
            try:
                pfad = os.path.join(wurzel, datei)
                if os.path.islink(pfad):
                    continue
                mtime = os.path.getmtime(pfad)
                if mtime < grenze:
                    groesse = os.path.getsize(pfad)
                    alter_tage = (datetime.now().timestamp() - mtime) / 86400
                    gefunden.append((groesse, alter_tage, pfad))
            except (OSError, PermissionError):
                pass

    if not gefunden:
        print("  Keine alten Dateien gefunden.")
        return

    gefunden.sort(reverse=True)
    total = sum(g for g, _, _ in gefunden)
    print(f"  {len(gefunden)} Dateien, {bytes_lesbar(total)} gesamt\n")
    print(f"  {'Groesse':<12} {'Alter':<10} Datei")
    print(f"  {'-'*60}")
    for groesse, tage, pfad in gefunden[:25]:
        jahre = tage / 365
        alter_str = f"{jahre:.1f}y"
        print(f"  {bytes_lesbar(groesse):<12} {alter_str:<10} {pfad.replace(HOME, '~')}")
    if len(gefunden) > 25:
        print(f"  ... ({len(gefunden) - 25} weitere nicht angezeigt)")
    print(f"\n  Tipp: Pruefe ob diese Dateien noch benoetigt werden.")

def mail_analysieren():
    print("\nMail-Ordner analysieren ...\n")

    mail_pfad = os.path.join(HOME, "Library", "Mail")
    if not os.path.exists(mail_pfad):
        print("  Kein Mail-Ordner gefunden.")
        return

    # Gesamtgroesse Mail-Store
    print("  Berechne Groesse (kann einen Moment dauern) ...")
    total = ordner_groesse(mail_pfad)
    print(f"\n  Mail-Store gesamt: {bytes_lesbar(total)}")

    # Einzelne Accounts
    v_ordner = sorted(
        [d for d in os.listdir(mail_pfad)
         if os.path.isdir(os.path.join(mail_pfad, d)) and d.startswith("V")],
        reverse=True
    )
    if v_ordner:
        v_pfad = os.path.join(mail_pfad, v_ordner[0])
        accounts = [d for d in os.listdir(v_pfad)
                    if os.path.isdir(os.path.join(v_pfad, d))]
        if accounts:
            print(f"\n  Accounts ({v_ordner[0]}):")
            account_groessen = []
            for acc in accounts:
                groesse = ordner_groesse(os.path.join(v_pfad, acc))
                account_groessen.append((groesse, acc))
            for groesse, acc in sorted(account_groessen, reverse=True):
                print(f"  {bytes_lesbar(groesse):<12} {acc}")

    # Downloads-Ordner
    downloads = os.path.join(HOME, "Library", "Mail Downloads")
    if os.path.exists(downloads):
        dl_groesse = ordner_groesse(downloads)
        print(f"\n  Mail Downloads: {bytes_lesbar(dl_groesse)}")

    print("\n  Tipp: Geloeschte Mails bereinigen in")
    print("  Mail > Postfach > Geloeschte Objekte entfernen.")

def systeminfo_anzeigen():
    print("\nSystem-Informationen ...\n")

    def sysctl(key):
        try:
            return subprocess.run(["sysctl", "-n", key],
                capture_output=True, text=True).stdout.strip()
        except Exception:
            return "?"

    # macOS
    vers = subprocess.run(["sw_vers"], capture_output=True, text=True).stdout.strip()
    for zeile in vers.splitlines():
        print(f"  {zeile}")

    # CPU & RAM
    cpu = sysctl("machdep.cpu.brand_string")
    ram_bytes = int(sysctl("hw.memsize") or 0)
    print(f"\n  CPU:    {cpu}")
    print(f"  RAM:    {bytes_lesbar(ram_bytes)}")

    # RAM-Nutzung via vm_stat
    try:
        vm = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
        seitengroesse = 16384
        def vmwert(schluessel):
            for zeile in vm.splitlines():
                if schluessel in zeile:
                    return int(''.join(filter(str.isdigit, zeile))) * seitengroesse
            return 0
        belegt = vmwert("Pages active") + vmwert("Pages wired down")
        print(f"  RAM genutzt: {bytes_lesbar(belegt)} / {bytes_lesbar(ram_bytes)}")
    except Exception:
        pass

    # Uptime
    boot = sysctl("kern.boottime")
    try:
        sek = int(boot.split("sec = ")[1].split(",")[0])
        uptime_h = (datetime.now().timestamp() - sek) / 3600
        if uptime_h < 24:
            print(f"  Uptime: {uptime_h:.1f} Stunden")
        else:
            print(f"  Uptime: {uptime_h/24:.1f} Tage")
    except Exception:
        pass

    # Festplatte
    disk = shutil.disk_usage("/")
    print(f"\n  Festplatte: {bytes_lesbar(disk.used)} belegt / {bytes_lesbar(disk.total)} total ({disk.used/disk.total*100:.0f}%)")
    print(f"  Frei:       {bytes_lesbar(disk.free)}")

    # Akku (nur bei MacBooks)
    try:
        akku = subprocess.run(["pmset", "-g", "batt"],
            capture_output=True, text=True).stdout
        for zeile in akku.splitlines():
            if "%" in zeile:
                print(f"\n  Akku: {zeile.strip()}")
                break
    except Exception:
        pass

def duplikate_suchen():
    print("\nDuplikate suchen ...\n")
    print("  Analysiere Dateien (kann einen Moment dauern) ...")

    groessen = {}
    for wurzel, ordner, dateien in os.walk(HOME):
        ordner[:] = [o for o in ordner if not o.startswith(".")
                     and o not in ["Library", "Applications"]]
        for datei in dateien:
            pfad = os.path.join(wurzel, datei)
            try:
                if os.path.islink(pfad):
                    continue
                groesse = os.path.getsize(pfad)
                if groesse < 1024:
                    continue
                groessen.setdefault(groesse, []).append(pfad)
            except (OSError, PermissionError):
                pass

    # Nur Gruppen mit mehreren Dateien hashen
    dupgruppen = []
    for groesse, pfade in groessen.items():
        if len(pfade) < 2:
            continue
        hashes = {}
        for pfad in pfade:
            try:
                h = hashlib.md5()
                with open(pfad, "rb") as f:
                    while chunk := f.read(65536):
                        h.update(chunk)
                hashes.setdefault(h.hexdigest(), []).append(pfad)
            except (OSError, PermissionError):
                pass
        for duplist in hashes.values():
            if len(duplist) > 1:
                dupgruppen.append((groesse, duplist))

    if not dupgruppen:
        print("  Keine Duplikate gefunden.")
        return

    dupgruppen.sort(reverse=True)
    total_verschwendet = sum(g * (len(d) - 1) for g, d in dupgruppen)
    print(f"\n  {len(dupgruppen)} Duplikat-Gruppen gefunden")
    print(f"  Einsparpotenzial: {bytes_lesbar(total_verschwendet)}\n")
    print(f"  {'Groesse':<12} Dateien")
    print(f"  {'-'*60}")
    for groesse, duplist in dupgruppen[:15]:
        print(f"  {bytes_lesbar(groesse):<12} ({len(duplist)}x)")
        for pfad in duplist:
            print(f"               {pfad.replace(HOME, '~')}")
    if len(dupgruppen) > 15:
        print(f"\n  ... ({len(dupgruppen) - 15} weitere Gruppen nicht angezeigt)")
    print("\n  Tipp: Duplikate manuell pruefen und loeschen —")
    print("  das Tool loescht keine Duplikate automatisch.")

def sprachdateien_bereinigen():
    print("\nSprachdateien in Apps analysieren ...\n")

    # Systemsprache ermitteln
    try:
        lang_out = subprocess.run(
            ["defaults", "read", "-g", "AppleLanguages"],
            capture_output=True, text=True
        ).stdout
        sys_lang = None
        for z in lang_out.splitlines():
            z = z.strip().strip('",').split("-")[0]
            if len(z) == 2 and z.isalpha():
                sys_lang = z
                break
        sys_lang = sys_lang or "de"
    except Exception:
        sys_lang = "de"

    behalten = {sys_lang, "en", "Base"}
    print(f"  Behalte: {', '.join(sorted(behalten))}\n")

    loeschbar = []
    apps = []
    for ordner in ["/Applications", os.path.join(HOME, "Applications")]:
        if os.path.exists(ordner):
            apps += [os.path.join(ordner, a)
                     for a in os.listdir(ordner) if a.endswith(".app")]

    for app in apps:
        res_pfad = os.path.join(app, "Contents", "Resources")
        if not os.path.exists(res_pfad):
            continue
        for eintrag in os.listdir(res_pfad):
            if not eintrag.endswith(".lproj"):
                continue
            lang = eintrag.replace(".lproj", "").split("-")[0]
            if lang in behalten:
                continue
            pfad = os.path.join(res_pfad, eintrag)
            groesse = ordner_groesse(pfad)
            loeschbar.append((groesse, pfad, os.path.basename(app)))

    if not loeschbar:
        print("  Keine entfernbaren Sprachdateien gefunden.")
        return

    loeschbar.sort(reverse=True)
    total = sum(g for g, _, _ in loeschbar)
    print(f"  {len(loeschbar)} Sprachdateien in {len({a for _, _, a in loeschbar})} Apps")
    print(f"  Einsparpotenzial: {bytes_lesbar(total)}\n")
    print(f"  {'Groesse':<12} {'App':<30} Sprache")
    print(f"  {'-'*60}")
    for groesse, pfad, app in loeschbar[:20]:
        lang = os.path.basename(pfad).replace(".lproj", "")
        print(f"  {bytes_lesbar(groesse):<12} {app:<30} {lang}")
    if len(loeschbar) > 20:
        print(f"  ... ({len(loeschbar) - 20} weitere)")

    antwort = input(f"\n  Alle nicht benoetigen Sprachdateien loeschen? (j/n): ").strip().lower()
    if antwort == "j":
        geloescht = 0
        for groesse, pfad, _ in loeschbar:
            try:
                shutil.rmtree(pfad)
                geloescht += groesse
            except Exception as e:
                print(f"  Fehler: {e}")
        print(f"  {bytes_lesbar(geloescht)} freigegeben.")
    else:
        print("  Nichts geloescht.")

# ── WARTUNG ───────────────────────────────────────────────────────────────────

def _sudo_ausfuehren(args, beschreibung):
    """Fuehrt einen sudo-Befehl aus und gibt Ergebnis zurueck."""
    print(f"  Fuehre aus: {' '.join(args)}")
    print("  (sudo-Passwort evtl. erforderlich)\n")
    try:
        ergebnis = subprocess.run(args, capture_output=False, text=True)
        if ergebnis.returncode == 0:
            print(f"\n  {beschreibung}: erledigt.")
        else:
            print(f"\n  Fehler beim Ausfuehren (Code {ergebnis.returncode}).")
    except FileNotFoundError:
        print(f"  Befehl nicht gefunden: {args[0]}")

def dns_cache_leeren():
    print("\nDNS-Cache leeren ...\n")
    print("  Benoetigt sudo-Rechte.\n")
    _sudo_ausfuehren(["sudo", "/usr/bin/dscacheutil", "-flushcache"], "dscacheutil")
    _sudo_ausfuehren(["sudo", "/usr/bin/killall", "-HUP", "mDNSResponder"], "mDNSResponder")
    print("  DNS-Cache wurde geleert.")

def spotlight_neu_indizieren():
    print("\nSpotlight neu indizieren ...\n")
    print("  Benoetigt sudo-Rechte. Die Neuindizierung laeuft im Hintergrund")
    print("  und kann einige Minuten dauern.\n")
    _sudo_ausfuehren(["sudo", "/usr/bin/mdutil", "-E", "/"], "Spotlight-Index geloescht")
    print("  Spotlight erstellt den Index automatisch neu.")

def wartungsskripte_ausfuehren():
    print("\nmacOS-Wartungsskripte ausfuehren ...\n")
    if not os.path.exists("/usr/sbin/periodic"):
        print("  Nicht verfuegbar: 'periodic' wurde in dieser macOS-Version entfernt.")
        print("  Die Wartungsaufgaben werden automatisch im Hintergrund von launchd verwaltet.")
        return
    print("  macOS hat eingebaute taegliche, woechentliche und monatliche")
    print("  Wartungsskripte (Log-Rotation, temp. Dateien, etc.).")
    print("  Benoetigt sudo-Rechte. Kann einige Minuten dauern.\n")
    antwort = input("  Alle drei Wartungsskripte jetzt ausfuehren? (j/n): ").strip().lower()
    if antwort == "j":
        _sudo_ausfuehren(["sudo", "/usr/sbin/periodic", "daily", "weekly", "monthly"],
                         "Wartungsskripte")
    else:
        print("  Abgebrochen.")

# ── MENUES ────────────────────────────────────────────────────────────────────

def submenu_bereinigung():
    while True:
        print("\n" + "-"*50)
        print("  BEREINIGUNG")
        print("-"*50)
        print("  1  App-Reste suchen und loeschen")
        print("  2  Grosse Dateien suchen (> 100 MB)")
        print("  3  Papierkorb leeren")
        print("  4  Homebrew-Cache bereinigen")
        print("  5  Browser-Caches bereinigen")
        print("  6  iOS-Backups anzeigen")
        print("  7  Gespeicherte App-Zustaende bereinigen")
        print("  8  Paketmanager-Caches bereinigen  (npm, pip, yarn ...)")
        print("  0  Zurueck")
        print("-"*50)
        auswahl = input("  Auswahl: ").strip()
        if auswahl == "1":
            app_reste_suchen()
        elif auswahl == "2":
            grosse_dateien_suchen()
        elif auswahl == "3":
            papierkorb_leeren()
        elif auswahl == "4":
            brew_cache_bereinigen()
        elif auswahl == "5":
            browser_cache_bereinigen()
        elif auswahl == "6":
            ios_backups_anzeigen()
        elif auswahl == "7":
            gespeicherte_zustaende_bereinigen()
        elif auswahl == "8":
            paketmanager_cache_bereinigen()
        elif auswahl == "0":
            break
        else:
            print("\n  Ungueltige Auswahl.")

def submenu_leistung():
    while True:
        print("\n" + "-"*50)
        print("  LEISTUNG")
        print("-"*50)
        print("  1  Login-Objekte anzeigen")
        print("  2  Defekte LaunchAgents entfernen")
        print("  3  Entwickler-Cache bereinigen  (Xcode, Simulatoren)")
        print("  4  Downloads-Ordner analysieren")
        print("  5  Festplattennutzung anzeigen")
        print("  6  App deinstallieren")
        print("  7  Alte Dateien suchen  (> 1 Jahr nicht veraendert)")
        print("  8  Mail-Ordner analysieren")
        print("  9  Duplikate suchen")
        print("  0  Zurueck")
        print("-"*50)
        auswahl = input("  Auswahl: ").strip()
        if auswahl == "1":
            login_objekte_anzeigen()
        elif auswahl == "2":
            defekte_launch_agenten_entfernen()
        elif auswahl == "3":
            entwickler_cache_bereinigen()
        elif auswahl == "4":
            downloads_analysieren()
        elif auswahl == "5":
            festplattennutzung_anzeigen()
        elif auswahl == "6":
            app_deinstallieren()
        elif auswahl == "7":
            alte_dateien_suchen()
        elif auswahl == "8":
            mail_analysieren()
        elif auswahl == "9":
            duplikate_suchen()
        elif auswahl == "0":
            break
        else:
            print("\n  Ungueltige Auswahl.")

def submenu_wartung():
    while True:
        print("\n" + "-"*50)
        print("  WARTUNG                         [sudo]")
        print("-"*50)
        print("  1  DNS-Cache leeren")
        print("  2  Spotlight neu indizieren")
        print("  3  macOS-Wartungsskripte ausfuehren")
        print("  4  System-Informationen anzeigen")
        print("  5  Sprachdateien bereinigen")
        print("  0  Zurueck")
        print("-"*50)
        auswahl = input("  Auswahl: ").strip()
        if auswahl == "1":
            dns_cache_leeren()
        elif auswahl == "2":
            spotlight_neu_indizieren()
        elif auswahl == "3":
            wartungsskripte_ausfuehren()
        elif auswahl == "4":
            systeminfo_anzeigen()
        elif auswahl == "5":
            sprachdateien_bereinigen()
        elif auswahl == "0":
            break
        else:
            print("\n  Ungueltige Auswahl.")

def hauptmenu():
    print("\n" + "="*50)
    print("  mac-cleaner")
    print("="*50)
    print("  1  Bereinigung")
    print("     App-Reste, Dateien, Papierkorb, Brew, Browser, Zustaende")
    print("  2  Leistung")
    print("     Disk-Nutzung, App-Deinstallation, Downloads, LaunchAgents")
    print("  3  Wartung                         [sudo]")
    print("     DNS, Spotlight, macOS-Skripte")
    print("  0  Beenden")
    print("="*50)
    return input("  Auswahl: ").strip()

def main():
    while True:
        auswahl = hauptmenu()
        if auswahl == "1":
            submenu_bereinigung()
        elif auswahl == "2":
            submenu_leistung()
        elif auswahl == "3":
            submenu_wartung()
        elif auswahl == "0":
            print("\n  Tschuess!\n")
            break
        else:
            print("\n  Ungueltige Auswahl.")

if __name__ == "__main__":
    main()

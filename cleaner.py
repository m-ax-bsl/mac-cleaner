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

def temp_dateien_bereinigen():
    print("\nTemporaere Dateien bereinigen ...\n")

    kandidaten = [
        ("TemporaryItems",  "~/Library/Caches/TemporaryItems"),
        ("CloudKit-Cache",  "~/Library/Caches/CloudKit"),
        ("FaceTime-Cache",  "~/Library/Caches/com.apple.FaceTime.FTVideoEncoding"),
    ]

    # /private/tmp: nur eigene Dateien loeschen
    import getpass
    username = getpass.getuser()
    tmp_pfad = "/private/tmp"
    eigene_tmp = []
    if os.path.exists(tmp_pfad):
        try:
            for name in os.listdir(tmp_pfad):
                pfad = os.path.join(tmp_pfad, name)
                try:
                    import stat
                    st = os.stat(pfad)
                    if st.st_uid == os.getuid():
                        groesse = ordner_groesse(pfad)
                        eigene_tmp.append((groesse, pfad))
                except (OSError, PermissionError):
                    pass
        except PermissionError:
            pass

    loeschbar = []
    for label, pfad_tmpl in kandidaten:
        pfad = os.path.expanduser(pfad_tmpl)
        if not os.path.exists(pfad):
            continue
        groesse = ordner_groesse(pfad)
        if groesse == 0:
            continue
        kurz = pfad.replace(HOME, "~")
        print(f"  {label:<22} {bytes_lesbar(groesse):<12} {kurz}")
        loeschbar.append((label, groesse, pfad))

    if eigene_tmp:
        tmp_total = sum(g for g, _ in eigene_tmp)
        print(f"  {'Eigene /tmp-Dateien':<22} {bytes_lesbar(tmp_total):<12} /private/tmp")
        for groesse, pfad in eigene_tmp:
            loeschbar.append((os.path.basename(pfad), groesse, pfad))

    if not loeschbar:
        print("  Keine temporaeren Dateien gefunden.")
        return

    total = sum(g for _, g, _ in loeschbar)
    print(f"\n  Total: {bytes_lesbar(total)}")

    antwort = input("\n  Temporaere Dateien loeschen? (j/n): ").strip().lower()
    if antwort == "j":
        for label, groesse, pfad in loeschbar:
            try:
                if os.path.isdir(pfad):
                    shutil.rmtree(pfad)
                    os.makedirs(pfad, exist_ok=True)
                else:
                    os.remove(pfad)
                print(f"  Geloescht: {label} ({bytes_lesbar(groesse)})")
            except Exception as e:
                print(f"  Fehler bei {label}: {e}")
        print(f"\n  {bytes_lesbar(total)} freigegeben.")
    else:
        print("  Nichts geloescht.")


def app_store_cache_bereinigen():
    print("\nApp Store Cache bereinigen ...\n")

    kandidaten = [
        ("App Store Cache",    "~/Library/Caches/com.apple.appstore"),
        ("StoreKit Cache",     "~/Library/Caches/com.apple.storekitd"),
        ("App Store Updates",  "~/Library/Caches/com.apple.SoftwareUpdate"),
        ("App Store Assets",   "~/Library/Application Support/App Store"),
    ]

    loeschbar = []
    for label, pfad_tmpl in kandidaten:
        pfad = os.path.expanduser(pfad_tmpl)
        if not os.path.exists(pfad):
            continue
        groesse = ordner_groesse(pfad)
        if groesse == 0:
            continue
        kurz = pfad.replace(HOME, "~")
        print(f"  {label:<25} {bytes_lesbar(groesse):<12} {kurz}")
        loeschbar.append((label, groesse, pfad))

    if not loeschbar:
        print("  Keine App Store Caches gefunden.")
        return

    total = sum(g for _, g, _ in loeschbar)
    print(f"\n  Total: {bytes_lesbar(total)}")

    antwort = input("\n  App Store Caches loeschen? (j/n): ").strip().lower()
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


def crash_reports_bereinigen():
    print("\nCrash Reports bereinigen ...\n")

    orte = [
        ("Benutzer-Crashes",  os.path.join(HOME, "Library/Logs/DiagnosticReports")),
        ("Benutzer-Crashes (alt)", os.path.join(HOME, "Library/Logs/CrashReporter")),
    ]

    loeschbar = []
    for label, pfad in orte:
        if not os.path.exists(pfad):
            continue
        dateien = []
        try:
            for name in os.listdir(pfad):
                fp = os.path.join(pfad, name)
                if os.path.isfile(fp):
                    try:
                        groesse = os.path.getsize(fp)
                        mtime = os.path.getmtime(fp)
                        dateien.append((groesse, mtime, name, fp))
                    except OSError:
                        pass
        except PermissionError:
            pass
        if not dateien:
            continue
        total = sum(g for g, _, _, _ in dateien)
        print(f"  {label}: {len(dateien)} Dateien ({bytes_lesbar(total)})")
        dateien.sort(key=lambda x: x[1], reverse=True)
        for groesse, mtime, name, _ in dateien[:5]:
            datum = datetime.fromtimestamp(mtime).strftime("%d.%m.%Y")
            print(f"    {datum}  {bytes_lesbar(groesse):<10} {name}")
        if len(dateien) > 5:
            print(f"    ... ({len(dateien) - 5} weitere)")
        loeschbar.append((label, total, pfad, dateien))

    if not loeschbar:
        print("  Keine Crash Reports gefunden.")
        return

    gesamt = sum(t for _, t, _, _ in loeschbar)
    print(f"\n  Total: {bytes_lesbar(gesamt)}")

    antwort = input("\n  Alle Crash Reports loeschen? (j/n): ").strip().lower()
    if antwort == "j":
        for label, total, pfad, dateien in loeschbar:
            geloescht = 0
            for _, _, _, fp in dateien:
                try:
                    os.remove(fp)
                    geloescht += 1
                except Exception as e:
                    print(f"  Fehler: {e}")
            print(f"  {label}: {geloescht} Dateien geloescht")
        print(f"\n  {bytes_lesbar(gesamt)} freigegeben.")
    else:
        print("  Nichts geloescht.")


def installer_dateien_suchen():
    print("\nInstaller-Dateien suchen  (.dmg, .pkg, .iso) ...\n")
    print("  Analysiere Home-Verzeichnis ...")

    ENDUNGEN = {".dmg", ".pkg", ".iso", ".mpkg"}
    gefunden = []

    for wurzel, ordner, dateien in os.walk(HOME):
        ordner[:] = [o for o in ordner if not o.startswith(".")
                     and o not in ["Library", "Applications"]]
        for datei in dateien:
            _, ext = os.path.splitext(datei.lower())
            if ext not in ENDUNGEN:
                continue
            pfad = os.path.join(wurzel, datei)
            try:
                groesse = os.path.getsize(pfad)
                mtime = os.path.getmtime(pfad)
                alter_tage = (datetime.now().timestamp() - mtime) / 86400
                gefunden.append((groesse, alter_tage, pfad))
            except (OSError, PermissionError):
                pass

    if not gefunden:
        print("  Keine Installer-Dateien gefunden.")
        return

    gefunden.sort(reverse=True)
    total = sum(g for g, _, _ in gefunden)
    print(f"  {len(gefunden)} Dateien, {bytes_lesbar(total)} gesamt\n")
    print(f"  {'Groesse':<12} {'Alter':<10} Datei")
    print(f"  {'-'*60}")
    for groesse, tage, pfad in gefunden:
        alter_str = f"{int(tage)}d" if tage < 365 else f"{tage/365:.1f}y"
        print(f"  {bytes_lesbar(groesse):<12} {alter_str:<10} {pfad.replace(HOME, '~')}")

    antwort = input("\n  Alle Installer-Dateien loeschen? (j/n): ").strip().lower()
    if antwort == "j":
        for _, _, pfad in gefunden:
            try:
                os.remove(pfad)
                print(f"  Geloescht: {pfad.replace(HOME, '~')}")
            except Exception as e:
                print(f"  Fehler: {e}")
        print(f"\n  {bytes_lesbar(total)} freigegeben.")
    else:
        print("  Nichts geloescht.")


def virtuelle_maschinen_suchen():
    print("\nVirtuelle Maschinen und Disk-Images suchen ...\n")
    print("  Analysiere Home-Verzeichnis ...")

    VM_ENDUNGEN = {".vmwarevm", ".pvm", ".vhd", ".vmdk", ".vdi", ".hdd",
                   ".qcow2", ".qcow", ".ovf", ".ova"}

    gefunden = []
    for wurzel, ordner, dateien in os.walk(HOME):
        # Bundles wie .vmwarevm direkt erkennen
        for name in list(ordner):
            _, ext = os.path.splitext(name.lower())
            if ext in VM_ENDUNGEN:
                pfad = os.path.join(wurzel, name)
                groesse = ordner_groesse(pfad)
                mtime = os.path.getmtime(pfad)
                alter_tage = (datetime.now().timestamp() - mtime) / 86400
                gefunden.append((groesse, alter_tage, pfad))
                ordner.remove(name)
        # Einzelne Disk-Image-Dateien
        for datei in dateien:
            _, ext = os.path.splitext(datei.lower())
            if ext in VM_ENDUNGEN:
                pfad = os.path.join(wurzel, datei)
                try:
                    groesse = os.path.getsize(pfad)
                    mtime = os.path.getmtime(pfad)
                    alter_tage = (datetime.now().timestamp() - mtime) / 86400
                    gefunden.append((groesse, alter_tage, pfad))
                except (OSError, PermissionError):
                    pass

    if not gefunden:
        print("  Keine virtuellen Maschinen oder Disk-Images gefunden.")
        return

    gefunden.sort(reverse=True)
    total = sum(g for g, _, _ in gefunden)
    print(f"  {len(gefunden)} Eintraege, {bytes_lesbar(total)} gesamt\n")
    print(f"  {'Groesse':<12} {'Alter':<10} Datei")
    print(f"  {'-'*60}")
    for groesse, tage, pfad in gefunden:
        alter_str = f"{int(tage)}d" if tage < 365 else f"{tage/365:.1f}y"
        print(f"  {bytes_lesbar(groesse):<12} {alter_str:<10} {pfad.replace(HOME, '~')}")
    print("\n  Tipp: Nicht mehr benoetigte VMs koennen sicher geloescht werden.")


def archive_analysieren():
    print("\nArchive und komprimierte Dateien suchen ...\n")
    print("  Analysiere Home-Verzeichnis ...")

    ENDUNGEN = {".zip", ".tar", ".gz", ".bz2", ".xz", ".rar", ".7z",
                ".tgz", ".tbz2", ".tar.gz", ".tar.bz2"}

    gefunden = []
    for wurzel, ordner, dateien in os.walk(HOME):
        ordner[:] = [o for o in ordner if not o.startswith(".")
                     and o not in ["Library", "Applications"]]
        for datei in dateien:
            name_lower = datei.lower()
            if not any(name_lower.endswith(ext) for ext in ENDUNGEN):
                continue
            pfad = os.path.join(wurzel, datei)
            try:
                groesse = os.path.getsize(pfad)
                mtime = os.path.getmtime(pfad)
                alter_tage = (datetime.now().timestamp() - mtime) / 86400
                gefunden.append((groesse, alter_tage, pfad))
            except (OSError, PermissionError):
                pass

    if not gefunden:
        print("  Keine Archive gefunden.")
        return

    gefunden.sort(reverse=True)
    total = sum(g for g, _, _ in gefunden)
    print(f"  {len(gefunden)} Archive, {bytes_lesbar(total)} gesamt\n")
    print(f"  {'Groesse':<12} {'Alter':<10} Datei")
    print(f"  {'-'*60}")
    for groesse, tage, pfad in gefunden[:25]:
        alter_str = f"{int(tage)}d" if tage < 365 else f"{tage/365:.1f}y"
        print(f"  {bytes_lesbar(groesse):<12} {alter_str:<10} {pfad.replace(HOME, '~')}")
    if len(gefunden) > 25:
        print(f"  ... ({len(gefunden) - 25} weitere)")

    alte = [(g, t, p) for g, t, p in gefunden if t > 180]
    if alte:
        alte_total = sum(g for g, _, _ in alte)
        print(f"\n  {len(alte)} Archive aelter als 6 Monate ({bytes_lesbar(alte_total)})")

    antwort = input("\n  Alle Archive loeschen? (j/n): ").strip().lower()
    if antwort == "j":
        for _, _, pfad in gefunden:
            try:
                os.remove(pfad)
                print(f"  Geloescht: {pfad.replace(HOME, '~')}")
            except Exception as e:
                print(f"  Fehler: {e}")
        print(f"\n  {bytes_lesbar(total)} freigegeben.")
    else:
        print("  Nichts geloescht.")


def user_caches_analysieren():
    print("\nUser-Caches analysieren ...\n")
    caches_pfad = os.path.join(HOME, "Library", "Caches")
    if not os.path.exists(caches_pfad):
        print("  Kein Caches-Ordner gefunden.")
        return

    print("  Berechne Groessen ...")
    eintraege = []
    try:
        for name in sorted(os.listdir(caches_pfad)):
            pfad = os.path.join(caches_pfad, name)
            groesse = ordner_groesse(pfad)
            eintraege.append((groesse, name, pfad))
    except PermissionError:
        pass

    eintraege.sort(reverse=True)
    total = sum(g for g, _, _ in eintraege)
    print(f"  {len(eintraege)} Eintraege, {bytes_lesbar(total)} gesamt\n")
    print(f"  {'Groesse':<12} Cache")
    print(f"  {'-'*55}")
    for groesse, name, _ in eintraege[:25]:
        print(f"  {bytes_lesbar(groesse):<12} {name}")
    if len(eintraege) > 25:
        print(f"  ... ({len(eintraege) - 25} weitere)")

    apps = installierte_apps()
    loeschbar = [
        (g, n, p) for g, n, p in eintraege
        if not ist_systemdatei(n) and ist_app_rest(n, apps)
    ]
    if loeschbar:
        loeschbar_total = sum(g for g, _, _ in loeschbar)
        print(f"\n  Nicht installierte Apps: {len(loeschbar)} Caches ({bytes_lesbar(loeschbar_total)})")
        antwort = input("  Diese Caches loeschen? (j/n): ").strip().lower()
        if antwort == "j":
            for groesse, name, pfad in loeschbar:
                try:
                    if os.path.isdir(pfad):
                        shutil.rmtree(pfad)
                    else:
                        os.remove(pfad)
                    print(f"  Geloescht: {name} ({bytes_lesbar(groesse)})")
                except Exception as e:
                    print(f"  Fehler bei {name}: {e}")
            print(f"\n  {bytes_lesbar(loeschbar_total)} freigegeben.")
        else:
            print("  Nichts geloescht.")
    else:
        print("\n  Alle Caches gehoeren installierten Apps.")


def logs_bereinigen():
    print("\nLog-Dateien analysieren ...\n")

    log_orte = [
        os.path.join(HOME, "Library", "Logs"),
    ]

    alle = []
    for basis in log_orte:
        if not os.path.exists(basis):
            continue
        try:
            for name in sorted(os.listdir(basis)):
                pfad = os.path.join(basis, name)
                groesse = ordner_groesse(pfad)
                mtime = os.path.getmtime(pfad)
                alter_tage = (datetime.now().timestamp() - mtime) / 86400
                alle.append((groesse, alter_tage, name, pfad))
        except PermissionError:
            pass

    if not alle:
        print("  Keine Log-Dateien gefunden.")
        return

    alle.sort(reverse=True)
    total = sum(g for g, _, _, _ in alle)
    print(f"  {len(alle)} Eintraege, {bytes_lesbar(total)} gesamt\n")
    print(f"  {'Groesse':<12} {'Alter':<10} Name")
    print(f"  {'-'*55}")
    for groesse, tage, name, _ in alle[:20]:
        alter_str = f"{int(tage)}d" if tage < 365 else f"{tage/365:.1f}y"
        print(f"  {bytes_lesbar(groesse):<12} {alter_str:<10} {name}")
    if len(alle) > 20:
        print(f"  ... ({len(alle) - 20} weitere)")

    # System-Logs ausschliessen (DiagnosticReports ist separate Funktion)
    loeschbar = [
        (g, t, n, p) for g, t, n, p in alle
        if not ist_systemdatei(n) or t > 30
    ]
    loeschbar_total = sum(g for g, _, _, _ in loeschbar)
    print(f"\n  Loeschbar: {len(loeschbar)} Eintraege ({bytes_lesbar(loeschbar_total)})")

    antwort = input("\n  Alle Logs loeschen? (j/n): ").strip().lower()
    if antwort == "j":
        for groesse, _, name, pfad in loeschbar:
            try:
                if os.path.isdir(pfad):
                    shutil.rmtree(pfad)
                else:
                    os.remove(pfad)
                print(f"  Geloescht: {name} ({bytes_lesbar(groesse)})")
            except Exception as e:
                print(f"  Fehler bei {name}: {e}")
        print(f"\n  {bytes_lesbar(loeschbar_total)} freigegeben.")
    else:
        print("  Nichts geloescht.")


def screenshots_aufraeumen():
    print("\nScreenshots suchen ...\n")

    suchpfade = [
        os.path.join(HOME, "Desktop"),
        os.path.join(HOME, "Documents"),
        os.path.join(HOME, "Pictures"),
        os.path.join(HOME, "Downloads"),
    ]

    SCREENSHOT_MUSTER = [
        "Screenshot ",
        "Bildschirmfoto ",
        "Screen Shot ",
        "Bildschirmaufnahme ",
        "CleanShot ",
    ]

    gefunden = []
    for basis in suchpfade:
        if not os.path.exists(basis):
            continue
        for name in os.listdir(basis):
            if not any(name.startswith(m) for m in SCREENSHOT_MUSTER):
                continue
            pfad = os.path.join(basis, name)
            try:
                groesse = os.path.getsize(pfad) if os.path.isfile(pfad) else ordner_groesse(pfad)
                mtime = os.path.getmtime(pfad)
                alter_tage = (datetime.now().timestamp() - mtime) / 86400
                gefunden.append((groesse, alter_tage, name, pfad))
            except (OSError, PermissionError):
                pass

    if not gefunden:
        print("  Keine Screenshots gefunden.")
        return

    gefunden.sort(key=lambda x: x[1], reverse=True)
    total = sum(g for g, _, _, _ in gefunden)
    print(f"  {len(gefunden)} Screenshots, {bytes_lesbar(total)} gesamt\n")
    print(f"  {'Groesse':<12} {'Alter':<10} Name")
    print(f"  {'-'*60}")
    for groesse, tage, name, _ in gefunden[:20]:
        alter_str = f"{int(tage)}d" if tage < 365 else f"{tage/365:.1f}y"
        print(f"  {bytes_lesbar(groesse):<12} {alter_str:<10} {name}")
    if len(gefunden) > 20:
        print(f"  ... ({len(gefunden) - 20} weitere)")

    alte = [(g, t, n, p) for g, t, n, p in gefunden if t > 90]
    if alte:
        alte_total = sum(g for g, _, _, _ in alte)
        print(f"\n  {len(alte)} Screenshots aelter als 90 Tage ({bytes_lesbar(alte_total)})")

    antwort = input("\n  Alle Screenshots loeschen? (j/n): ").strip().lower()
    if antwort == "j":
        for _, _, name, pfad in gefunden:
            try:
                os.remove(pfad)
                print(f"  Geloescht: {name}")
            except Exception as e:
                print(f"  Fehler bei {name}: {e}")
        print(f"\n  {bytes_lesbar(total)} freigegeben.")
    else:
        print("  Nichts geloescht.")


def icloud_analyse():
    print("\niCloud Drive analysieren ...\n")

    icloud_pfad = os.path.join(HOME, "Library", "Mobile Documents", "com~apple~CloudDocs")
    if not os.path.exists(icloud_pfad):
        # Alternativer Pfad
        icloud_pfad = os.path.join(HOME, "iCloud Drive (Archiv)")
        if not os.path.exists(icloud_pfad):
            print("  iCloud Drive nicht gefunden.")
            print("  Tipp: iCloud Drive unter ~/Library/Mobile Documents/com~apple~CloudDocs")
            return

    print("  Berechne Groessen (kann einen Moment dauern) ...")
    eintraege = []
    try:
        for name in sorted(os.listdir(icloud_pfad)):
            if name.startswith("."):
                continue
            pfad = os.path.join(icloud_pfad, name)
            groesse = ordner_groesse(pfad)
            eintraege.append((groesse, name))
    except PermissionError:
        print("  Kein Zugriff auf iCloud Drive.")
        return

    eintraege.sort(reverse=True)
    total = sum(g for g, _ in eintraege)

    print(f"\n  iCloud Drive gesamt: {bytes_lesbar(total)}\n")
    print(f"  {'Groesse':<12} {'':20} Ordner/Datei")
    print(f"  {'-'*55}")
    balken_max = eintraege[0][0] if eintraege else 1
    for groesse, name in eintraege[:20]:
        balken = int(groesse / balken_max * 15) if balken_max > 0 else 0
        print(f"  {bytes_lesbar(groesse):<12} {'█' * balken:<15} {name}")
    if len(eintraege) > 20:
        print(f"  ... ({len(eintraege) - 20} weitere)")


def system_erweiterungen():
    print("\nSystem-Erweiterungen anzeigen ...\n")

    # System Extensions (macOS 10.15+)
    sys_ext_pfad = "/Library/SystemExtensions"
    gefunden = False
    if os.path.exists(sys_ext_pfad):
        try:
            ergebnis = subprocess.run(
                ["systemextensionsctl", "list"],
                capture_output=True, text=True
            )
            if ergebnis.returncode == 0 and ergebnis.stdout.strip():
                print("  Installierte System-Erweiterungen:\n")
                for zeile in ergebnis.stdout.splitlines():
                    if zeile.strip() and not zeile.startswith("---"):
                        print(f"  {zeile}")
                gefunden = True
        except FileNotFoundError:
            pass

    # Kernel Extensions (aelter, /Library/Extensions)
    kext_pfad = "/Library/Extensions"
    kexts = []
    if os.path.exists(kext_pfad):
        try:
            kexts = [f for f in os.listdir(kext_pfad) if f.endswith(".kext")]
        except PermissionError:
            pass
    if kexts:
        print(f"\n  Kernel Extensions ({kext_pfad}):\n")
        for kext in sorted(kexts):
            print(f"  • {kext}")
        gefunden = True

    # User-installierte Kernel Extensions
    user_kext = os.path.join(HOME, "Library", "Extensions")
    if os.path.exists(user_kext):
        try:
            user_kexts = [f for f in os.listdir(user_kext) if f.endswith(".kext")]
            if user_kexts:
                print(f"\n  Benutzer Kernel Extensions (~/Library/Extensions):\n")
                for kext in sorted(user_kexts):
                    print(f"  • {kext}")
                gefunden = True
        except PermissionError:
            pass

    if not gefunden:
        print("  Keine System-Erweiterungen oder Kernel Extensions gefunden.")

    print("\n  Tipp: Unbekannte Erweiterungen koennen in")
    print("  Systemeinstellungen > Datenschutz > Sicherheit verwaltet werden.")


def docker_bereinigen():
    print("\nDocker bereinigen ...\n")

    docker = shutil.which("docker")
    if not docker:
        print("  Docker nicht installiert.")
        return

    # Pruefen ob Docker-Daemon laeuft
    ping = subprocess.run([docker, "info"], capture_output=True, text=True)
    if ping.returncode != 0:
        print("  Docker ist nicht gestartet. Bitte zuerst Docker starten.")
        return

    # Vorschau: docker system df
    df = subprocess.run([docker, "system", "df"], capture_output=True, text=True)
    if df.returncode == 0:
        print("  Docker Speichernutzung:\n")
        for zeile in df.stdout.splitlines():
            print(f"  {zeile}")

    # Nicht verwendete Ressourcen anzeigen
    prunable = subprocess.run(
        [docker, "system", "df", "--format", "{{.Reclaimable}}"],
        capture_output=True, text=True
    )

    print()
    antwort = input("  Ungenutzte Docker-Ressourcen bereinigen? (j/n): ").strip().lower()
    if antwort == "j":
        print("\n  Fuehre docker system prune aus ...")
        result = subprocess.run(
            [docker, "system", "prune", "-f"],
            capture_output=False, text=True
        )
        if result.returncode == 0:
            print("  Docker bereinigt.")
        else:
            print("  Fehler beim Bereinigen.")
    else:
        print("  Nichts bereinigt.")


def schriften_analysieren():
    print("\nSchriften analysieren ...\n")

    schrift_orte = [
        ("Benutzer",  os.path.join(HOME, "Library", "Fonts")),
        ("System",    "/Library/Fonts"),
        ("macOS",     "/System/Library/Fonts"),
    ]

    alle_schriften = {}
    for label, pfad in schrift_orte:
        if not os.path.exists(pfad):
            continue
        try:
            dateien = [f for f in os.listdir(pfad)
                       if f.lower().endswith((".ttf", ".otf", ".ttc", ".dfont", ".woff", ".woff2"))]
        except PermissionError:
            dateien = []
        groesse = sum(
            os.path.getsize(os.path.join(pfad, f))
            for f in dateien
            if not os.path.islink(os.path.join(pfad, f))
        )
        print(f"  {label:<12} {len(dateien):>4} Schriften  {bytes_lesbar(groesse)}")
        for f in dateien:
            name_ohne_ext = os.path.splitext(f)[0].lower()
            alle_schriften.setdefault(name_ohne_ext, []).append(os.path.join(pfad, f))

    # Duplikate (gleicher Name in mehreren Ordnern)
    duplikate = {n: pfade for n, pfade in alle_schriften.items() if len(pfade) > 1}
    if duplikate:
        print(f"\n  {len(duplikate)} Schriften in mehreren Ordnern:\n")
        for name, pfade in sorted(duplikate.items())[:10]:
            print(f"  {name}")
            for p in pfade:
                print(f"    {p.replace(HOME, '~')}")

    # Benutzer-Schriften anzeigen
    benutzer_pfad = os.path.join(HOME, "Library", "Fonts")
    if os.path.exists(benutzer_pfad):
        try:
            user_fonts = sorted([f for f in os.listdir(benutzer_pfad)
                                 if f.lower().endswith((".ttf", ".otf", ".ttc", ".dfont"))])
            if user_fonts:
                print(f"\n  Eigene Schriften (~{benutzer_pfad.replace(HOME, '~')}):")
                for f in user_fonts[:20]:
                    groesse = os.path.getsize(os.path.join(benutzer_pfad, f))
                    print(f"  {bytes_lesbar(groesse):<10} {f}")
                if len(user_fonts) > 20:
                    print(f"  ... ({len(user_fonts) - 20} weitere)")
        except PermissionError:
            pass


def browser_erweiterungen():
    print("\nBrowser-Erweiterungen anzeigen ...\n")

    def msg_auflösen(verzeichnis, schluessel):
        import json, re
        m = re.match(r"^__MSG_(.+?)__$", schluessel)
        if not m:
            return schluessel
        msg_key = m.group(1)
        for lang in ["en", "de", "en_US"]:
            mp = os.path.join(verzeichnis, "_locales", lang, "messages.json")
            if not os.path.exists(mp):
                continue
            try:
                with open(mp, encoding="utf-8", errors="ignore") as f:
                    msgs = json.load(f)
                for k, v in msgs.items():
                    if k.lower() == msg_key.lower():
                        return v.get("message", schluessel)
            except Exception:
                pass
        return schluessel

    def manifest_lesen(verzeichnis):
        import json
        for manifest in ["manifest.json", "Info.plist"]:
            mp = os.path.join(verzeichnis, manifest)
            if not os.path.exists(mp):
                continue
            try:
                if manifest.endswith(".json"):
                    with open(mp, encoding="utf-8", errors="ignore") as f:
                        data = json.load(f)
                    name = data.get("name", "")
                    if name.startswith("__MSG_"):
                        name = msg_auflösen(verzeichnis, name)
                    return name, data.get("version", "")
                else:
                    with open(mp, "rb") as f:
                        data = plistlib.load(f)
                    name = data.get("CFBundleDisplayName") or data.get("CFBundleName", "")
                    return name, data.get("CFBundleShortVersionString", "")
            except Exception:
                pass
        return "", ""

    def erweiterungen_aus_pfad(pfad, browser):
        erw = []
        if not os.path.exists(pfad):
            return erw
        try:
            for ext_id in os.listdir(pfad):
                ep = os.path.join(pfad, ext_id)
                if not os.path.isdir(ep):
                    continue
                # Chromium: ext_id/version/manifest.json
                titel, version = manifest_lesen(ep)
                if not titel:
                    try:
                        sub = sorted(os.listdir(ep))
                        for s in sub:
                            sp = os.path.join(ep, s)
                            if os.path.isdir(sp):
                                titel, version = manifest_lesen(sp)
                                if titel:
                                    break
                    except PermissionError:
                        pass
                erw.append((titel or ext_id, version))
        except PermissionError:
            pass
        return erw

    browser_pfade = [
        ("Chrome",   "~/Library/Application Support/Google/Chrome/Default/Extensions"),
        ("Brave",    "~/Library/Application Support/BraveSoftware/Brave-Browser/Default/Extensions"),
        ("Edge",     "~/Library/Application Support/Microsoft Edge/Default/Extensions"),
        ("Chromium", "~/Library/Application Support/Chromium/Default/Extensions"),
        ("Firefox",  "~/Library/Application Support/Firefox/Profiles"),
        ("Safari",   "~/Library/Safari/Extensions"),
    ]

    gesamt = 0
    for browser, pfad_tmpl in browser_pfade:
        pfad = os.path.expanduser(pfad_tmpl)
        erw = erweiterungen_aus_pfad(pfad, browser)
        if not erw:
            continue
        gesamt += len(erw)
        print(f"  {browser} ({len(erw)} Erweiterungen):")
        for titel, version in sorted(erw):
            v_str = f"  v{version}" if version else ""
            print(f"    • {titel}{v_str}")
        print()

    if gesamt == 0:
        print("  Keine Browser-Erweiterungen gefunden.")
    else:
        print(f"  Total: {gesamt} Erweiterungen")
        print("  Tipp: Unbekannte Erweiterungen in den Browser-Einstellungen deaktivieren.")


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

def leere_ordner_finden():
    print("\nLeere Ordner suchen ...\n")
    print("  Analysiere Home-Verzeichnis ...")

    BUNDLE_ENDUNGEN = {
        ".app", ".photoslibrary", ".sparsebundle", ".sparseimage",
        ".xcodeproj", ".xcworkspace", ".framework", ".kext", ".bundle",
        ".pages", ".numbers", ".key", ".keynote", ".sketch",
        ".git", ".svn", ".hg",
    }

    def pfad_ueberspringen(pfad):
        teile = pfad.replace(HOME, "").split(os.sep)
        for teil in teile:
            if not teil:
                continue
            if teil.startswith("."):
                return True
            if any(teil.endswith(ext) for ext in BUNDLE_ENDUNGEN):
                return True
        return False

    leere = []
    skip_erste_ebene = {"Library", "Applications", ".Trash"}
    for wurzel, ordner, dateien in os.walk(HOME, topdown=False):
        if wurzel == HOME:
            continue
        relativ = wurzel.replace(HOME + os.sep, "")
        erste_ebene = relativ.split(os.sep)[0]
        if erste_ebene in skip_erste_ebene:
            continue
        if pfad_ueberspringen(wurzel):
            continue
        try:
            inhalt = os.listdir(wurzel)
            if not inhalt:
                leere.append(wurzel)
        except PermissionError:
            pass

    if not leere:
        print("  Keine leeren Ordner gefunden.")
        return

    print(f"  {len(leere)} leere Ordner gefunden:\n")
    for pfad in leere[:30]:
        print(f"  {pfad.replace(HOME, '~')}")
    if len(leere) > 30:
        print(f"  ... ({len(leere) - 30} weitere)")

    antwort = input("\n  Alle leeren Ordner loeschen? (j/n): ").strip().lower()
    if antwort == "j":
        geloescht = 0
        for pfad in leere:
            try:
                os.rmdir(pfad)
                geloescht += 1
            except Exception:
                pass
        print(f"  {geloescht} leere Ordner geloescht.")
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

def mail_anhaenge_analysieren():
    print("\nMail-Anhaenge analysieren ...\n")

    mail_pfad = os.path.join(HOME, "Library", "Mail")
    if not os.path.exists(mail_pfad):
        print("  Kein Mail-Ordner gefunden.")
        return

    print("  Suche Anhaenge (kann einen Moment dauern) ...")
    anhaenge = []
    for wurzel, ordner, dateien in os.walk(mail_pfad):
        if "Attachments" not in wurzel.split(os.sep):
            continue
        for datei in dateien:
            if datei.startswith("."):
                continue
            pfad = os.path.join(wurzel, datei)
            try:
                groesse = os.path.getsize(pfad)
                if groesse > 0:
                    anhaenge.append((groesse, pfad))
            except (OSError, PermissionError):
                pass

    if not anhaenge:
        print("  Keine Mail-Anhaenge gefunden.")
        return

    anhaenge.sort(reverse=True)
    total = sum(g for g, _ in anhaenge)
    print(f"  {len(anhaenge)} Anhaenge, {bytes_lesbar(total)} gesamt\n")

    # Nach Typ gruppieren
    typen = {}
    for groesse, pfad in anhaenge:
        ext = os.path.splitext(pfad)[1].lower() or "(kein)"
        typen[ext] = typen.get(ext, 0) + groesse

    print("  Nach Dateityp:")
    for ext, groesse in sorted(typen.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {ext:<15} {bytes_lesbar(groesse)}")

    print(f"\n  Groesste Anhaenge:")
    for groesse, pfad in anhaenge[:10]:
        print(f"  {bytes_lesbar(groesse):<12} {os.path.basename(pfad)}")

    print("\n  Tipp: Mail-Anhaenge in Mail > Ablage > Anhaenge entfernen.")


def time_machine_snapshots():
    print("\nTime Machine Snapshots ...\n")

    ergebnis = subprocess.run(
        ["tmutil", "listlocalsnapshots", "/"],
        capture_output=True, text=True
    )
    if ergebnis.returncode != 0 or not ergebnis.stdout.strip():
        print("  Keine lokalen Snapshots gefunden.")
        return

    snapshots = [s.strip() for s in ergebnis.stdout.strip().splitlines() if s.strip()]
    print(f"  {len(snapshots)} lokale Snapshots:\n")
    for snap in snapshots:
        # Format: com.apple.TimeMachine.2024-01-15-123456.local
        datum = snap.replace("com.apple.TimeMachine.", "").replace(".local", "")
        print(f"  • {datum}")

    print(f"\n  Hinweis: Snapshots werden automatisch geloescht wenn")
    print(f"  der Speicher knapp wird. Manuell loeschen via:")
    print(f"  tmutil deletelocalsnapshots <datum>")

    antwort = input("\n  Alle lokalen Snapshots loeschen? (j/n): ").strip().lower()
    if antwort == "j":
        for snap in snapshots:
            datum = snap.replace("com.apple.TimeMachine.", "").replace(".local", "")
            print(f"  Loesche {datum} ...")
            r = subprocess.run(
                ["tmutil", "deletelocalsnapshots", datum],
                capture_output=True, text=True
            )
            if r.returncode == 0:
                print(f"  Geloescht: {datum}")
            else:
                print(f"  Fehler: {r.stderr.strip()}")
    else:
        print("  Nichts geloescht.")


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
    print("\nmacOS-Wartungsaufgaben ...\n")

    LSREGISTER = (
        "/System/Library/Frameworks/CoreServices.framework"
        "/Frameworks/LaunchServices.framework/Support/lsregister"
    )
    ATSUTIL = "/usr/bin/atsutil"

    print("  1  LaunchServices-Datenbank neu aufbauen")
    print("     Behebt Probleme mit 'Oeffnen mit'-Menue und Datei-Zuordnungen")
    print("  2  Schriften-Cache bereinigen")
    print("     Behebt Darstellungsfehler bei Schriften  [sudo]")
    print("  3  Beide ausfuehren")
    print("  0  Abbrechen\n")
    auswahl = input("  Auswahl: ").strip()

    if auswahl in ("1", "3"):
        print("\n  Baue LaunchServices-Datenbank neu auf ...")
        _sudo_ausfuehren(
            ["sudo", LSREGISTER, "-kill", "-r",
             "-domain", "local", "-domain", "system", "-domain", "user"],
            "LaunchServices-Datenbank"
        )

    if auswahl in ("2", "3"):
        if os.path.exists(ATSUTIL):
            print("\n  Bereinige Schriften-Cache ...")
            _sudo_ausfuehren(["sudo", ATSUTIL, "databases", "-remove"],
                             "Schriften-Cache geloescht")
            _sudo_ausfuehren(["sudo", ATSUTIL, "server", "-shutdown"],
                             "Schriften-Server neugestartet")
        else:
            print("  atsutil nicht gefunden — Schriften-Cache kann nicht geleert werden.")

    if auswahl == "0":
        print("  Abgebrochen.")

def ram_freigeben():
    print("\nRAM freigeben ...\n")

    def ram_frei():
        try:
            vm = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
            seitengroesse = 16384
            def vmwert(schluessel):
                for zeile in vm.splitlines():
                    if schluessel in zeile:
                        return int(''.join(filter(str.isdigit, zeile))) * seitengroesse
                return 0
            frei = vmwert("Pages free") + vmwert("Pages speculative")
            return frei
        except Exception:
            return 0

    frei_vorher = ram_frei()
    print(f"  Freier RAM (vorher): {bytes_lesbar(frei_vorher)}")
    print("  Fuehre 'purge' aus ...  [sudo]\n")
    _sudo_ausfuehren(["sudo", "/usr/sbin/purge"], "RAM-Cache geleert")
    frei_nachher = ram_frei()
    print(f"\n  Freier RAM (nachher): {bytes_lesbar(frei_nachher)}")
    gewonnen = frei_nachher - frei_vorher
    if gewonnen > 0:
        print(f"  Freigegeben: {bytes_lesbar(gewonnen)}")


def netzwerk_info():
    print("\nNetzwerk-Informationen ...\n")

    # Aktive Netzwerk-Interfaces
    try:
        ifconfig = subprocess.run(["ifconfig"], capture_output=True, text=True).stdout
        aktiv = []
        iface = None
        for zeile in ifconfig.splitlines():
            if not zeile.startswith("\t") and not zeile.startswith(" "):
                iface = zeile.split(":")[0]
            if iface and "inet " in zeile and "127.0.0.1" not in zeile:
                ip = zeile.strip().split()[1]
                aktiv.append((iface, ip))
        if aktiv:
            print("  IP-Adressen:")
            for iface, ip in aktiv:
                print(f"  {iface:<12} {ip}")
    except Exception:
        pass

    # WiFi SSID
    try:
        for iface in ["en0", "en1"]:
            r = subprocess.run(
                ["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-I"],
                capture_output=True, text=True
            )
            for zeile in r.stdout.splitlines():
                if " SSID:" in zeile:
                    ssid = zeile.split("SSID:")[1].strip()
                    print(f"\n  WiFi SSID:   {ssid}")
                    break
            break
    except Exception:
        pass

    # DNS-Server
    try:
        dns = subprocess.run(["scutil", "--dns"], capture_output=True, text=True).stdout
        server = []
        for zeile in dns.splitlines():
            if "nameserver[" in zeile:
                ip = zeile.split(":")[1].strip()
                if ip not in server:
                    server.append(ip)
        if server:
            print(f"\n  DNS-Server:  {', '.join(server[:3])}")
    except Exception:
        pass

    # Standard-Gateway
    try:
        route = subprocess.run(["route", "get", "default"], capture_output=True, text=True).stdout
        for zeile in route.splitlines():
            if "gateway:" in zeile:
                gw = zeile.split("gateway:")[1].strip()
                print(f"  Gateway:     {gw}")
                break
    except Exception:
        pass

    # Offene Verbindungen (Anzahl)
    try:
        netstat = subprocess.run(
            ["netstat", "-an", "-p", "tcp"],
            capture_output=True, text=True
        ).stdout
        established = sum(1 for z in netstat.splitlines() if "ESTABLISHED" in z)
        listen = sum(1 for z in netstat.splitlines() if "LISTEN" in z)
        print(f"\n  TCP-Verbindungen: {established} aktiv, {listen} lauschend")
    except Exception:
        pass


def datenschutz_bereinigen():
    print("\nDatensschutz-Caches bereinigen ...\n")

    kandidaten = [
        ("QuickLook-Vorschau",  "~/Library/Caches/com.apple.QuickLook.thumbnailcache"),
        ("Recents-Listen",      "~/Library/Application Support/com.apple.sharedfilelist"),
        ("Kurzbefehl-Vorlagen", "~/Library/Application Support/com.apple.shortcuts"),
        ("Notification-Cache",  "~/Library/Caches/com.apple.notificationcenter"),
        ("Siri-Vorschlaege",    "~/Library/Application Support/com.apple.suggestions"),
    ]

    loeschbar = []
    for label, pfad_tmpl in kandidaten:
        pfad = os.path.expanduser(pfad_tmpl)
        if not os.path.exists(pfad):
            continue
        groesse = ordner_groesse(pfad)
        kurz = pfad.replace(HOME, "~")
        print(f"  {label:<26} {bytes_lesbar(groesse):<12} {kurz}")
        loeschbar.append((label, groesse, pfad))

    if not loeschbar:
        print("  Keine Datenschutz-Caches gefunden.")
        return

    total = sum(g for _, g, _ in loeschbar)
    print(f"\n  Total: {bytes_lesbar(total)}")
    print("  Hinweis: Recents-Listen und QuickLook werden automatisch neu aufgebaut.")

    antwort = input("\n  Datenschutz-Caches loeschen? (j/n): ").strip().lower()
    if antwort == "j":
        for label, groesse, pfad in loeschbar:
            try:
                if os.path.isdir(pfad):
                    shutil.rmtree(pfad)
                else:
                    os.remove(pfad)
                print(f"  Geloescht: {label} ({bytes_lesbar(groesse)})")
            except Exception as e:
                print(f"  Fehler bei {label}: {e}")
        print(f"\n  {bytes_lesbar(total)} freigegeben.")
    else:
        print("  Nichts geloescht.")


def virusscan_ausfuehren():
    print("\nVirus-Scan (ClamAV) ...\n")

    clamscan = shutil.which("clamscan")
    freshclam_bin = shutil.which("freshclam")

    if not clamscan:
        print("  ClamAV ist nicht installiert.\n")
        print("  Installation via Homebrew:")
        print("    brew install clamav\n")
        print("  Signaturen danach einmalig initialisieren:")

        # Pfad zur freshclam.conf ermitteln
        for basis in ["/opt/homebrew/etc/clamav", "/usr/local/etc/clamav"]:
            sample = os.path.join(basis, "freshclam.conf.sample")
            conf   = os.path.join(basis, "freshclam.conf")
            if os.path.exists(sample):
                print(f"    cp {sample} {conf}")
                print(f"    sed -i '' 's/^Example/#Example/' {conf}")
                break
        print("    freshclam")
        return

    # ClamAV-Version anzeigen
    v = subprocess.run([clamscan, "--version"], capture_output=True, text=True)
    print(f"  {v.stdout.strip()}")

    # Signatur-Datenbank prüfen
    db_pfade = [
        "/opt/homebrew/var/lib/clamav",
        "/usr/local/var/lib/clamav",
        "/var/lib/clamav",
    ]
    db_datum = None
    for db_pfad in db_pfade:
        main_cvd = os.path.join(db_pfad, "main.cvd")
        daily_cvd = os.path.join(db_pfad, "daily.cvd")
        daily_cld = os.path.join(db_pfad, "daily.cld")
        for f in [daily_cld, daily_cvd, main_cvd]:
            if os.path.exists(f):
                mtime = os.path.getmtime(f)
                db_datum = datetime.fromtimestamp(mtime)
                break
        if db_datum:
            break

    if db_datum:
        alter = (datetime.now() - db_datum).days
        status = "aktuell" if alter < 3 else f"VERALTET ({alter} Tage alt)"
        print(f"  Signaturen: {db_datum.strftime('%d.%m.%Y')}  [{status}]\n")
    else:
        print("  Signaturen: nicht gefunden — bitte 'freshclam' ausfuehren\n")

    # Scan-Ziel wählen
    print("  Scan-Bereich:")
    print("  1  Downloads")
    print("  2  Desktop")
    print("  3  Home-Verzeichnis  (kann mehrere Minuten dauern)")
    print("  4  Eigenen Pfad eingeben")
    print("  0  Abbrechen\n")

    auswahl = input("  Auswahl: ").strip()
    if auswahl == "0":
        return
    elif auswahl == "1":
        ziel = os.path.join(HOME, "Downloads")
    elif auswahl == "2":
        ziel = os.path.join(HOME, "Desktop")
    elif auswahl == "3":
        ziel = HOME
    elif auswahl == "4":
        ziel = os.path.expanduser(input("  Pfad: ").strip())
        if not os.path.exists(ziel):
            print(f"  Pfad nicht gefunden: {ziel}")
            return
    else:
        print("  Ungueltige Auswahl.")
        return

    # Signaturen aktualisieren
    if freshclam_bin:
        upd = input("\n  Signaturen aktualisieren? (j/n): ").strip().lower()
        if upd == "j":
            print("  Aktualisiere Signaturen ...\n")
            subprocess.run([freshclam_bin], capture_output=False)
            print()

    print(f"  Scanne: {ziel}")
    print("  (kann einige Minuten dauern — Ctrl+C zum Abbrechen)\n")

    try:
        result = subprocess.run(
            [clamscan, "-r", "--infected", "--no-summary", ziel],
            capture_output=True, text=True
        )
        # Zusammenfassung separat
        summary = subprocess.run(
            [clamscan, "-r", "--infected", ziel],
            capture_output=True, text=True
        )
    except KeyboardInterrupt:
        print("\n  Scan abgebrochen.")
        return

    infiziert = [z for z in result.stdout.splitlines() if "FOUND" in z]

    # Zusammenfassung aus Summary-Lauf
    for zeile in summary.stdout.splitlines():
        key = zeile.split(":")[0].strip() if ":" in zeile else ""
        if key in ("Scanned files", "Infected files", "Time", "Data scanned",
                   "Scanned directories"):
            print(f"  {zeile.strip()}")

    if infiziert:
        print(f"\n  WARNUNG: {len(infiziert)} Bedrohung(en) gefunden!\n")
        for f in infiziert:
            print(f"  {f}")
        print("\n  Tipp: Infizierte Dateien manuell pruefen und loeschen.")
    else:
        print("\n  Keine Bedrohungen gefunden.")


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
        print("  9  Temporaere Dateien bereinigen")
        print("  A  App Store Cache bereinigen")
        print("  B  Crash Reports loeschen")
        print("  C  Installer-Dateien suchen  (.dmg, .pkg, .iso)")
        print("  D  Virtuelle Maschinen suchen  (.vmwarevm, .pvm, .vhd ...)")
        print("  E  Archive suchen  (.zip, .tar.gz, .rar ...)")
        print("  F  User-Caches analysieren")
        print("  G  Log-Dateien bereinigen")
        print("  H  Screenshots aufraeumen")
        print("  I  Docker bereinigen")
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
        elif auswahl == "9":
            temp_dateien_bereinigen()
        elif auswahl.upper() == "A":
            app_store_cache_bereinigen()
        elif auswahl.upper() == "B":
            crash_reports_bereinigen()
        elif auswahl.upper() == "C":
            installer_dateien_suchen()
        elif auswahl.upper() == "D":
            virtuelle_maschinen_suchen()
        elif auswahl.upper() == "E":
            archive_analysieren()
        elif auswahl.upper() == "F":
            user_caches_analysieren()
        elif auswahl.upper() == "G":
            logs_bereinigen()
        elif auswahl.upper() == "H":
            screenshots_aufraeumen()
        elif auswahl.upper() == "I":
            docker_bereinigen()
        elif auswahl == "0":
            break
        else:
            print("\n  Ungueltige Auswahl.")

def prozesse_analysieren():
    print("\nLaufende Prozesse analysieren ...\n")

    # Top-Prozesse nach CPU
    try:
        cpu_out = subprocess.run(
            ["ps", "-eo", "pid,%cpu,%mem,rss,comm", "-r"],
            capture_output=True, text=True
        ).stdout.splitlines()
    except Exception:
        print("  Fehler beim Abfragen der Prozesse.")
        return

    prozesse = []
    for zeile in cpu_out[1:]:
        teile = zeile.split(None, 4)
        if len(teile) < 5:
            continue
        try:
            pid  = int(teile[0])
            cpu  = float(teile[1])
            mem  = float(teile[2])
            rss  = int(teile[3]) * 1024
            name = os.path.basename(teile[4].strip())
            prozesse.append((cpu, mem, rss, pid, name))
        except ValueError:
            pass

    if not prozesse:
        print("  Keine Prozesse gefunden.")
        return

    print(f"  {'PID':<7} {'CPU %':<8} {'RAM %':<8} {'RAM':<10} Prozess")
    print(f"  {'-'*58}")
    for cpu, mem, rss, pid, name in prozesse[:20]:
        print(f"  {pid:<7} {cpu:<8.1f} {mem:<8.1f} {bytes_lesbar(rss):<10} {name}")

    total_ram = sum(r for _, _, r, _, _ in prozesse)
    print(f"\n  {len(prozesse)} Prozesse, {bytes_lesbar(total_ram)} RAM gesamt")

    # Beenden anbieten
    antwort = input("\n  PID eines Prozesses zum Beenden eingeben (oder Enter): ").strip()
    if antwort:
        try:
            kill_pid = int(antwort)
            treffer = [n for c, m, r, p, n in prozesse if p == kill_pid]
            name_str = treffer[0] if treffer else str(kill_pid)
            bestaetigung = input(f"  '{name_str}' (PID {kill_pid}) beenden? (j/n): ").strip().lower()
            if bestaetigung == "j":
                result = subprocess.run(["kill", str(kill_pid)], capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"  Prozess {kill_pid} beendet.")
                else:
                    print(f"  Fehler: {result.stderr.strip()}")
        except ValueError:
            print("  Ungueltige PID.")


def energie_analyse():
    print("\nEnergie-Analyse ...\n")

    # Akku-Status
    try:
        batt = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout
        print("  Akku:\n")
        for zeile in batt.strip().splitlines():
            print(f"  {zeile}")
    except Exception:
        pass

    # Energie-Einstellungen
    try:
        settings = subprocess.run(["pmset", "-g"], capture_output=True, text=True).stdout
        print("\n  Strom-Einstellungen:\n")
        wichtig = {"sleep", "displaysleep", "disksleep", "autopoweroff",
                   "powernap", "tcpkeepalive", "proximitywake"}
        for zeile in settings.strip().splitlines():
            schluessel = zeile.strip().split()[0] if zeile.strip() else ""
            if schluessel.lower() in wichtig:
                print(f"  {zeile.strip()}")
    except Exception:
        pass

    # Was verhindert Schlafmodus (Power Assertions) — gruppiert nach Prozess
    try:
        import re
        assertions = subprocess.run(
            ["pmset", "-g", "assertions"], capture_output=True, text=True
        ).stdout
        proz_sperren = {}
        for zeile in assertions.splitlines():
            if "PreventUserIdleSystemSleep" in zeile or "PreventSystemSleep" in zeile:
                m = re.search(r"pid\s+(\d+)\(([^)]+)\)", zeile)
                if m:
                    proz_sperren[m.group(2)] = int(m.group(1))
        if proz_sperren:
            print("\n  Schlafmodus wird verhindert durch:\n")
            for name, pid in sorted(proz_sperren.items()):
                print(f"  • {name}  (PID {pid})")
        else:
            print("\n  Keine aktiven Sleep-Sperren gefunden.")
    except Exception:
        pass

    # Systemlaufzeit und Temperaturen (falls verfuegbar)
    try:
        syslog = subprocess.run(
            ["sysctl", "-n", "kern.boottime"], capture_output=True, text=True
        ).stdout.strip()
        sek = int(syslog.split("sec = ")[1].split(",")[0])
        uptime_h = (datetime.now().timestamp() - sek) / 3600
        print(f"\n  Uptime: {uptime_h:.1f} h ({uptime_h/24:.1f} Tage)")
    except Exception:
        pass


def ssd_status():
    print("\nSSD / Festplatten-Status ...\n")

    # TRIM + Modell vom Haupt-Laufwerk
    try:
        trim_out = subprocess.run(
            ["system_profiler", "SPNVMeDataType"],
            capture_output=True, text=True, timeout=15
        ).stdout
        # Nur ersten Block auswerten (physisches Laufwerk, nicht Partitionen)
        modell = trim = kapazitaet = ""
        in_first_device = False
        for zeile in trim_out.splitlines():
            stripped = zeile.strip()
            if not stripped:
                if in_first_device and trim:
                    break
                continue
            if not zeile.startswith("    ") and stripped.endswith(":") and not in_first_device:
                in_first_device = True
                continue
            if in_first_device and ":" in stripped:
                key, _, val = stripped.partition(":")
                key = key.strip(); val = val.strip()
                if key in ("Model", "Device Model") and not modell:
                    modell = val
                if key == "TRIM Support" and not trim:
                    trim = "aktiviert" if val.lower() == "yes" else "DEAKTIVIERT"
                if key == "Capacity" and not kapazitaet:
                    kapazitaet = val.split("(")[0].strip()
        if modell:
            print(f"  Laufwerk: {modell}")
        if kapazitaet:
            print(f"  Kapazitaet: {kapazitaet}")
        if trim:
            print(f"  TRIM:     {trim}")
        elif not modell:
            # Fallback SATA
            sata = subprocess.run(
                ["system_profiler", "SPSerialATADataType"],
                capture_output=True, text=True, timeout=15
            ).stdout
            for zeile in sata.splitlines():
                if "TRIM" in zeile:
                    print(f"  {zeile.strip()}")
    except Exception as e:
        print(f"  TRIM-Info nicht verfuegbar: {e}")

    # Einhängepunkte (nur Haupt-Volumes, kein system-Kleinkram)
    print()
    try:
        df = subprocess.run(["df", "-g"], capture_output=True, text=True).stdout
        zeig = ["/", "/System/Volumes/Data"]
        extras = []
        for zeile in df.splitlines()[1:]:
            teile = zeile.split()
            if len(teile) < 6:
                continue
            mountpoint = teile[-1]
            if not teile[0].startswith("/dev/"):
                continue
            # Nur sinnvolle Einhängepunkte
            if mountpoint in zeig or mountpoint.startswith("/Volumes/"):
                extras.append(teile)
        if extras:
            print(f"  {'Volume':<20} {'Gesamt':>8} {'Belegt':>8} {'Frei':>8}  Pfad")
            print(f"  {'-'*58}")
            for t in extras:
                name = t[0].replace("/dev/", "")
                print(f"  {name:<20} {t[1]:>6} GB {t[2]:>6} GB {t[3]:>6} GB  {t[-1]}")
    except Exception:
        pass

    # SMART-Status
    print()
    try:
        smart = subprocess.run(
            ["diskutil", "info", "/dev/disk0"],
            capture_output=True, text=True
        ).stdout
        for zeile in smart.splitlines():
            if "SMART" in zeile:
                print(f"  {zeile.strip()}")
    except Exception:
        pass


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
        print("  A  Leere Ordner finden und loeschen")
        print("  B  Mail-Anhaenge analysieren")
        print("  C  Time Machine Snapshots anzeigen")
        print("  D  Schriften analysieren")
        print("  E  iCloud Drive analysieren")
        print("  F  Laufende Prozesse analysieren")
        print("  G  Energie-Analyse  (Akku, Schlafmodus)")
        print("  H  SSD / Festplatten-Status")
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
        elif auswahl.upper() == "A":
            leere_ordner_finden()
        elif auswahl.upper() == "B":
            mail_anhaenge_analysieren()
        elif auswahl.upper() == "C":
            time_machine_snapshots()
        elif auswahl.upper() == "D":
            schriften_analysieren()
        elif auswahl.upper() == "E":
            icloud_analyse()
        elif auswahl.upper() == "F":
            prozesse_analysieren()
        elif auswahl.upper() == "G":
            energie_analyse()
        elif auswahl.upper() == "H":
            ssd_status()
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
        print("  3  macOS-Wartungsaufgaben  (LaunchServices, Schriften)")
        print("  4  System-Informationen anzeigen")
        print("  5  Sprachdateien bereinigen")
        print("  6  RAM freigeben  [sudo]")
        print("  7  Datenschutz-Caches bereinigen")
        print("  8  Netzwerk-Informationen anzeigen")
        print("  9  Browser-Erweiterungen anzeigen")
        print("  A  System-Erweiterungen anzeigen")
        print("  B  Virus-Scan  (ClamAV)")
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
        elif auswahl == "6":
            ram_freigeben()
        elif auswahl == "7":
            datenschutz_bereinigen()
        elif auswahl == "8":
            netzwerk_info()
        elif auswahl == "9":
            browser_erweiterungen()
        elif auswahl.upper() == "A":
            system_erweiterungen()
        elif auswahl.upper() == "B":
            virusscan_ausfuehren()
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

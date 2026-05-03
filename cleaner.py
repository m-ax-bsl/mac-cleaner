#!/usr/bin/env python3
"""mac-cleaner — findet App-Reste und grosse Dateien"""

import os
import shutil

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

def grosse_dateien_suchen(min_mb=500):
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

def hauptmenu():
    print("\n" + "="*50)
    print("  mac-cleaner")
    print("="*50)
    print("  1  App-Reste suchen und loeschen")
    print("  2  Grosse Dateien suchen (> 500 MB)")
    print("  0  Beenden")
    print("="*50)
    return input("  Auswahl: ").strip()

def main():
    while True:
        auswahl = hauptmenu()
        if auswahl == "1":
            app_reste_suchen()
        elif auswahl == "2":
            grosse_dateien_suchen()
        elif auswahl == "0":
            print("\n  Tschuess!\n")
            break
        else:
            print("\n  Ungueltige Auswahl.")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""mac-cleaner — findet App-Reste und grosse Dateien"""

import os
import shutil

HOME = os.path.expanduser("~")

# Orte wo Apps Reste hinterlassen
APP_RESTE_ORTE = [
    "~/Library/Application Support",
    "~/Library/Preferences",
    "~/Library/Caches",
    "~/Library/Logs",
    "~/Library/Containers",
    "~/Library/Group Containers",
]

def bytes_lesbar(b):
    for einheit in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {einheit}"
        b /= 1024
    return f"{b:.1f} TB"

def grosse_dateien_suchen(min_mb=500):
    print(f"\n🔍 Suche Dateien grösser als {min_mb} MB ...\n")
    gefunden = []
    min_bytes = min_mb * 1024 * 1024
    suchpfade = [HOME]

    for pfad in suchpfade:
        for wurzel, ordner, dateien in os.walk(pfad):
            # Systempfade überspringen
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

    print(f"  {'Grösse':<12} Datei")
    print(f"  {'-'*60}")
    for groesse, pfad in gefunden[:20]:
        kurzer_pfad = pfad.replace(HOME, "~")
        print(f"  {bytes_lesbar(groesse):<12} {kurzer_pfad}")

    print(f"\n  {len(gefunden)} Dateien gefunden (zeige max. 20)")

def app_reste_suchen():
    print("\n🔍 Suche App-Reste ...\n")

    # Installierte Apps ermitteln
    installierte = set()
    for app_ordner in ["/Applications", os.path.join(HOME, "Applications")]:
        if os.path.exists(app_ordner):
            for name in os.listdir(app_ordner):
                if name.endswith(".app"):
                    installierte.add(name.replace(".app", "").lower())

    reste = []
    for ort in APP_RESTE_ORTE:
        pfad = os.path.expanduser(ort)
        if not os.path.exists(pfad):
            continue
        try:
            for eintrag in os.listdir(pfad):
                eintrag_lower = eintrag.lower()
                # Prüfen ob kein installiertes App dazu passt
                gefunden_app = any(
                    app in eintrag_lower or eintrag_lower in app
                    for app in installierte
                )
                if not gefunden_app:
                    voller_pfad = os.path.join(pfad, eintrag)
                    try:
                        if os.path.isdir(voller_pfad):
                            groesse = sum(
                                os.path.getsize(os.path.join(w, f))
                                for w, _, fs in os.walk(voller_pfad)
                                for f in fs
                                if not os.path.islink(os.path.join(w, f))
                            )
                        else:
                            groesse = os.path.getsize(voller_pfad)
                        kurzer_pfad = voller_pfad.replace(HOME, "~")
                        reste.append((groesse, kurzer_pfad, voller_pfad))
                    except (OSError, PermissionError):
                        pass
        except PermissionError:
            pass

    if not reste:
        print("  Keine App-Reste gefunden.")
        return

    reste.sort(reverse=True)
    print(f"  {'Grösse':<12} Pfad")
    print(f"  {'-'*60}")
    for groesse, kurz, _ in reste[:30]:
        print(f"  {bytes_lesbar(groesse):<12} {kurz}")

    print(f"\n  {len(reste)} mögliche Reste gefunden (zeige max. 30)")
    print("  Hinweis: Nicht alle sind wirklich Reste — prüfe vor dem Löschen.")

def hauptmenu():
    print("\n" + "="*50)
    print("  mac-cleaner")
    print("="*50)
    print("  1  Grosse Dateien suchen (> 500 MB)")
    print("  2  App-Reste suchen")
    print("  0  Beenden")
    print("="*50)
    return input("  Auswahl: ").strip()

def main():
    while True:
        auswahl = hauptmenu()
        if auswahl == "1":
            grosse_dateien_suchen()
        elif auswahl == "2":
            app_reste_suchen()
        elif auswahl == "0":
            print("\n  Tschüss!\n")
            break
        else:
            print("\n  Ungültige Auswahl.")

if __name__ == "__main__":
    main()

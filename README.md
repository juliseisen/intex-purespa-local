# Intex PureSpa (Tuya Local) — Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom%20Repository-orange.svg)](https://hacs.xyz/docs/faq/custom_repositories/)
![Version](https://img.shields.io/badge/Version-1.2.0-blue.svg)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-41BDF5.svg)

Lokale Steuerung eines **Tuya-basierten Intex PureSpa** („TY"-Bedienpanel) über das
Heimnetzwerk (TCP-Port 6668) — ohne Cloud im laufenden Betrieb.

Die Integration hält eine dauerhafte Verbindung zum Spa: Änderungen am Bedienteil
des Pools erscheinen **sofort** in Home Assistant (Push), zusätzlich wird der
komplette Status alle 30 Sekunden als Sicherheitsnetz abgefragt.

Entitäten:

| Entität | Funktion |
|---|---|
| Climate | Heizung ein/aus + Zieltemperatur (°C/°F automatisch erkannt) |
| Schalter | Power, Heizung, Filter, Bubbles, Jets*, Sanitizer* |
| Sensor | Aktuelle Wassertemperatur |
| Sensor (Diagnose) | Verbleibende Zeit, Raw Status (alle Tuya-Datenpunkte) |

\* nur wenn das Spa-Modell die Funktion meldet

## Voraussetzung: Geräte-ID und Local Key besorgen (einmalig)

Das Tuya-Lokalprotokoll ist verschlüsselt. Dafür braucht man den **Local Key** des
Geräts. Den bekommt man einmalig über die Tuya-Entwicklerplattform (kostenlos):

1. Der Spa muss in der **Smart Life**-App eingebunden sein.
2. Auf https://iot.tuya.com ein kostenloses Konto anlegen (Registrierung als
   „Skill Development" / Individual reicht).
3. **Cloud → Development → Create Cloud Project**.
   - Industry: *Smart Home*, Development Method: *Smart Home*
   - **Data Center: Central Europe Data Center** (wichtig, sonst wird das Gerät nicht gefunden!)
   - Bei den APIs mindestens **IoT Core** und **Authorization Token Management** aktivieren.
4. Im Projekt: **Devices → Link App Account → Add App Account**.
   Den angezeigten QR-Code mit der Smart-Life-App scannen
   (App: *Ich → ⚙/Scan-Symbol oben rechts*). Danach erscheint der Spa in der Geräteliste
   des Projekts — dort steht auch die **Device ID**.
5. **Cloud → API Explorer → Devices Management (oder „Device Control") →
   „Query Device Details"** öffnen, die Device ID eintragen und absenden.
   In der Antwort steht der **`local_key`** (ca. 16 Zeichen).

> **Wichtig:** Der Local Key ändert sich, sobald der Spa in der App gelöscht und neu
> angelernt wird. Danach muss der neue Key eingetragen werden
> (Integration entfernen und neu hinzufügen).

## Installation

### Variante A: Über HACS (empfohlen)

Die Integration ist über den **Home Assistant Community Store (HACS)** als
benutzerdefiniertes Repository installierbar. Vorteil: Updates erscheinen
automatisch in Home Assistant und lassen sich mit einem Klick einspielen.

**Voraussetzung:** [HACS](https://hacs.xyz/docs/use/download/download/) ist in
Home Assistant installiert.

1. In Home Assistant **HACS** in der Seitenleiste öffnen.
2. Oben rechts auf das **Drei-Punkte-Menü (⋮)** klicken → **„Benutzerdefinierte Repositories“**
   (englisch: *Custom repositories*).
3. Im Dialog eintragen:
   - **Repository:** `https://github.com/juliseisen/intex-purespa-local`
   - **Typ:** `Integration`
4. Auf **„Hinzufügen“** klicken und den Dialog schließen.
5. In HACS nach **„Intex PureSpa (Tuya Local)“** suchen, öffnen und unten rechts
   auf **„Herunterladen“** klicken (neueste Version auswählen).
6. Home Assistant **neu starten** (Einstellungen → System → Neu starten).
7. Weiter mit [Einrichtung](#einrichtung) unten.

**Updates:** Neue Versionen erscheinen automatisch unter
**Einstellungen → Geräte & Dienste → Updates** bzw. in HACS und können dort
direkt installiert werden. Nach jedem Update Home Assistant neu starten.

### Variante B: Manuell

1. Den Ordner `custom_components/intex_purespa` in das Home-Assistant-Konfigurationsverzeichnis
   kopieren (dort, wo auch `configuration.yaml` liegt): `config/custom_components/intex_purespa/`
2. Home Assistant **neu starten**.

> **Hinweis bei Umstieg von manueller Installation auf HACS:** Einfach Variante A
> durchführen — HACS überschreibt den vorhandenen Ordner. Die bestehende
> Konfiguration (Gerät, Local Key, Entitäten, Automationen) bleibt erhalten.

## Einrichtung

1. **Einstellungen → Geräte & Dienste → Integration hinzufügen → „Intex PureSpa (Tuya Local)"**
2. Eingeben:
   - **IP-Adresse** des Spa (am besten in der FRITZ!Box eine feste IP vergeben:
     Heimnetz → Netzwerk → Gerät bearbeiten → „Immer die gleiche IPv4-Adresse zuweisen")
   - **Device ID** und **Local Key** (siehe oben)
   - Protokollversion auf **auto** lassen — die Integration probiert 3.3/3.4/3.5/3.1
     automatisch durch und speichert die passende.

## Hinweise

- Tuya-Geräte erlauben lokal meist nur **eine Verbindung gleichzeitig**. Falls
  tuya-local/LocalTuya noch installiert sind und dasselbe Gerät ansprechen:
  dort das Gerät entfernen, sonst blockieren sich die Integrationen gegenseitig.
- Die Smart-Life-App funktioniert parallel weiter (sie läuft über die Cloud).
- Die offizielle Tuya-Integration in HA zeigt den Spa als „unbekannt" — das ist normal,
  sie kennt die Gerätekategorie des Spa nicht. Sie kann parallel installiert bleiben.
- Der Diagnose-Sensor **Raw Status** (standardmäßig deaktiviert) zeigt alle
  Tuya-Datenpunkte des Geräts — nützlich, falls dein Modell weitere Funktionen hat.

## Verbindungstest ohne Home Assistant (Windows, Node.js)

Mit `tools/test-connection.cjs` lässt sich die Verbindung vorab vom PC aus testen:

```
cd tools
npm install tuyapi
node test-connection.cjs <IP> <DEVICE_ID> <LOCAL_KEY>
```

Das Skript probiert alle Protokollversionen durch und gibt die Datenpunkte des Spa aus.

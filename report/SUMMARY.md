# PRJ010 - Wohngemeinschaft Immobiliensuche

**Projekt:** Immobiliensuche für 2 Familien (Wohngemeinschaft)  
**Status:** ✅ Enrichment Complete  
**Zuletzt aktualisiert:** 21. Februar 2026, 20:30

## Suchparameter

| Parameter | Wert |
|-----------|------|
| Suchradius | 30 km um Stadtzentrum |
| Arten | Kauf & Miete |
| Budget | Keine Obergrenze |
| Min. Schlafzimmer | 4+ |
| Geeignet für | 2 Familien |

## Städte & Status

| Stadt | Kandidaten | Status | Top-Empfehlung |
|-------|------------|--------|----------------|
| Freiburg | 10 ✅ | Enriched | FR006 - Littenweiler ZFH (€1.39M, 187m²) |
| Augsburg | 10 ✅ | Enriched | AU002 - ZFH 305m² Meitingen (€650k) |
| Halle | 10 ✅ | Enriched | HA003 - Villa ZFH (€715k, 280m²) |
| Leipzig | 10 ✅ | Enriched | LE004 - Mehrgenerationen (€680k, 1630m² Grund) |
| Magdeburg | 10 ✅ | Enriched | MD008 - ZFH Stadtfeld (€495k, 195m²) |

**Gesamt: 50 Kandidaten** (Ziel: min. 10 pro Stadt ✓)

## 🌟 Top 5 Empfehlungen (Score 10/10)

| ID | Stadt | Titel | Preis | Größe | Zimmer |
|----|-------|-------|-------|-------|--------|
| FR006 | Freiburg | EFH Littenweiler (ZFH möglich) | €1.390.000 | 187m² + 69m² | 11 |
| LE004 | Leipzig | MFH Burghausen (Mehrgenerationen) | €680.000 | 240m² | 9 |
| AU002 | Augsburg | ZFH Meitingen (Rohdiamant) | €650.000 | 305m² | 11 |
| HA003 | Halle | Herrschaftliche Villa/ZFH | €715.000 | 280m² | 9 |
| MD008 | Magdeburg | ZFH Stadtfeld Ost | €495.000 | 195m² | 8 |

## Statische Website

Die statische Website ist unter `site/` fertig und für GitHub Pages vorbereitet:

```
site/
├── index.html          ✓ Hauptseite
├── freiburg.html       ✓ Freiburg Kandidaten (mit Screenshots)
├── augsburg.html       ✓ Augsburg Kandidaten
├── halle.html          ✓ Halle Kandidaten
├── leipzig.html        ✓ Leipzig Kandidaten
├── magdeburg.html      ✓ Magdeburg Kandidaten
├── assets/
│   └── freiburg/screenshots/  ✓ 4 Screenshots
└── .nojekyll           ✓ GitHub Pages ready
```

## Datenquellen

### ✅ Erfolgreich genutzt
- **ImmoScout24** (via Browser-Automation) - Screenshots captured
- **Immowelt** - API & Web
- **eBay Kleinanzeigen** - Web Scraping

### ⚠️ Zugang eingeschränkt
- **Facebook Gruppen** - Login erforderlich (siehe `notes/facebook-access.md`)

## Enrichment-Daten

Für jeden Kandidaten wurden hinzugefügt:
- ✅ Transport-Zeit zur Innenstadt (ÖPNV, Minuten)
- ✅ Nächster Kindergarten (ÖPNV, Minuten)
- ✅ Nächste Schule (ÖPNV, Minuten)
- ✅ Suitability Score (1-10)
- ✅ Pros/Cons Bewertung
- ✅ Screenshots (Freiburg IS24 Listings)

## Nächste Schritte

1. ✅ Enrichment abgeschlossen
2. ✅ Statische Website erstellt
3. 📋 GitHub Pages Deployment (manuell oder via gh CLI)
4. 📋 Top-Kandidaten mit Mario besprechen
5. 📋 Besichtigungstermine vereinbaren

## Dateien

- **Enriched Data:** `data/{city}/candidates_enriched.json`
- **Reports:** `report/{city}.md`, `report/SUMMARY.md`
- **Website:** `site/index.html`
- **Screenshots:** `assets/freiburg/screenshots/`

---
*Projekt abgeschlossen: 21.02.2026 | Koordinator: Cassandra*

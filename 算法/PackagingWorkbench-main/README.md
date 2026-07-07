<div align="center">

<img src="resources/icons/Packaging.svg" width="96" alt="Packaging Workbench"/>

# Packaging Workbench for FreeCAD

[![License: LGPL v2.1](https://img.shields.io/badge/License-LGPL%20v2.1-blue.svg)](LICENSE)
[![FreeCAD](https://img.shields.io/badge/FreeCAD-1.0%2B-brightgreen.svg)](https://www.freecad.org)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org)
[![Version](https://img.shields.io/badge/version-1.0.0-orange.svg)](CHANGELOG.md)

> Parametric design of cardboard boxes and dielines following FEFCO standards.
> An open-source alternative to commercial packaging CAD.

[🇮🇹 Italiano](#-italiano) · [🇬🇧 English](#-english)

</div>

---

## 🇮🇹 Italiano

### Cos'è Packaging?

**Packaging** è un workbench per FreeCAD 1.0+ per la **progettazione parametrica
di scatole in cartone** secondo gli standard FEFCO, con **generazione automatica
della fustella 2D** (piano di taglio) esportabile in DXF. Colma un vuoto del
mondo open source: finora il packaging in cartone richiedeva software
commerciali costosi (ArtiosCAD, Picador).

### Caratteristiche

- **Tre tipi di scatola FEFCO** supportati (0201, 0301, 0713)
- **Geometria 3D scoppiata** parametrica (alette aperte a 90°, chiaramente
  leggibile)
- **Generazione fustella 2D piatta** con layer separati Cut / Crease /
  Perforation
- **Export DXF** nativo (tramite l'importatore di FreeCAD)
- Tutte le scatole sono **parametriche**: cambia Length / Width / Height (e gli
  altri parametri) e la scatola si rigenera automaticamente
- Nessuna dipendenza esterna: usa solo i moduli core di FreeCAD

### Installazione (manuale)

1. Scarica o clona il repository.
2. Copia (o crea un collegamento) la cartella nella `Mod` di FreeCAD —
   **attenzione alla versione**:
   - Windows FreeCAD 1.0.x: `%APPDATA%\FreeCAD\Mod\Packaging`
   - Windows FreeCAD 1.1.x: `%APPDATA%\FreeCAD\v1-1\Mod\Packaging`
   - Linux: `~/.local/share/FreeCAD/Mod/Packaging`
   - macOS: `~/Library/Application Support/FreeCAD/Mod/Packaging`

   Su Windows una **junction** non richiede privilegi di amministratore:
   ```powershell
   New-Item -ItemType Junction `
     -Path "$env:APPDATA\FreeCAD\Mod\Packaging" `
     -Target "C:\percorso\a\PackagingWorkbench"
   ```
3. Riavvia FreeCAD.
4. Seleziona il workbench **Packaging** dal selettore.

Una volta pubblicato, sarà installabile anche tramite l'**Addon Manager**.

### Uso rapido

1. Attiva il workbench **Packaging**.
2. Clicca **FEFCO 0201 box** (o 0301 / 0713): la scatola 3D parametrica compare
   nel documento.
3. Nel pannello **Data** modifica `Length` / `Width` / `Height` / `Thickness`:
   la scatola si rigenera.
4. **Seleziona** la scatola e clicca **Generate dieline**: la fustella 2D piatta
   appare sotto la scatola, con i layer Cut (rosso) / Crease (blu) /
   Perforation.
5. Esporta la fustella: seleziona il gruppo `*_Dieline` → **File → Esporta** →
   `.dxf`.

### Tipi di scatole supportati

| Codice | Nome | Descrizione |
|--------|------|-------------|
| **FEFCO 0201** | Regular Slotted Container | La classica "scatola americana" |
| **FEFCO 0301** | Tray and Lid | Vassoio + coperchio (due pezzi) |
| **FEFCO 0713** | Tuck-end carton | Astuccio retail con linguette a infilare |

---

## 🇬🇧 English

### What is Packaging?

**Packaging** is a FreeCAD 1.0+ workbench for the **parametric design of
cardboard boxes** following FEFCO standards, with **automatic 2D dieline**
(cutting plan) generation exportable to DXF. It fills an open-source gap:
cardboard packaging design previously required expensive commercial software
(ArtiosCAD, Picador).

### Features

- **Three FEFCO box types** supported (0201, 0301, 0713)
- **Parametric exploded 3D geometry** (flaps opened at 90°, easy to read)
- **Flat 2D dieline generation** with separate Cut / Crease / Perforation layers
- **Native DXF export** (via FreeCAD's importer)
- Every box is **parametric**: change Length / Width / Height (and the other
  parameters) and it rebuilds automatically
- No external dependencies: uses only FreeCAD core modules

### Installation (manual)

1. Download or clone the repository.
2. Copy (or link) the folder into FreeCAD's `Mod` directory — **mind the
   version**:
   - Windows FreeCAD 1.0.x: `%APPDATA%\FreeCAD\Mod\Packaging`
   - Windows FreeCAD 1.1.x: `%APPDATA%\FreeCAD\v1-1\Mod\Packaging`
   - Linux: `~/.local/share/FreeCAD/Mod/Packaging`
   - macOS: `~/Library/Application Support/FreeCAD/Mod/Packaging`

   On Windows a **junction** does not require administrator rights:
   ```powershell
   New-Item -ItemType Junction `
     -Path "$env:APPDATA\FreeCAD\Mod\Packaging" `
     -Target "C:\path\to\PackagingWorkbench"
   ```
3. Restart FreeCAD.
4. Pick the **Packaging** workbench from the selector.

Once published, it will also be installable through the **Addon Manager**.

### Quick start

1. Activate the **Packaging** workbench.
2. Click **FEFCO 0201 box** (or 0301 / 0713): the parametric 3D box appears.
3. In the **Data** panel change `Length` / `Width` / `Height` / `Thickness`: the
   box rebuilds.
4. **Select** the box and click **Generate dieline**: the flat 2D dieline
   appears below the box, with Cut (red) / Crease (blue) / Perforation layers.
5. Export it: select the `*_Dieline` group → **File → Export** → `.dxf`.

### Supported box types

| Code | Name | Description |
|------|------|-------------|
| **FEFCO 0201** | Regular Slotted Container | The classic "American" shipping box |
| **FEFCO 0301** | Tray and Lid | Tray + cover (two pieces) |
| **FEFCO 0713** | Tuck-end carton | Retail carton with tuck-in flaps |

---

## Screenshots

| | |
|---|---|
| ![FEFCO 0201](docs/screenshots/fefco0201.png) | ![FEFCO 0301](docs/screenshots/fefco0301.png) |
| ![FEFCO 0713](docs/screenshots/fefco0713.png) | ![Dieline](docs/screenshots/dieline.png) |

_(Add your screenshots under `docs/screenshots/`.)_

## Development / Testing

The test suite runs under a plain Python interpreter (FreeCAD's API is mocked),
so no FreeCAD installation is required to run it:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Style: `black --line-length 100` and `ruff`. Code and comments in English;
user-facing documentation in Italian + English.

## License

LGPL-2.1-or-later — see the [`LICENSE`](LICENSE) file.

## Contributing

Pull requests are welcome. Please keep the existing conventions (Conventional
Commits, one feature branch per change) and make sure the test suite stays
green.

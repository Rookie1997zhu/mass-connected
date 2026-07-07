# CLAUDE.md — Packaging Workbench

This file stores the original project brief and working conventions so any
future Claude Code session (or contributor) has the full context.

---

## Project brief (original prompt)

Sei un esperto sviluppatore di workbench FreeCAD. Devi creare DA ZERO un
workbench Python per FreeCAD 1.0 chiamato "Packaging" per la progettazione
parametrica di scatole e fustelle in cartone.

### Contesto del progetto

Nel panorama FreeCAD esistono workbench per lamiera (SheetMetal), incastri
laser (LCInterlocking), legno (Woodworking), ma manca un workbench dedicato
al packaging in cartone. Software commerciali (ArtiosCAD, Picador) costano
migliaia di euro. Questo progetto colma quel vuoto in open source.

### Stack tecnico

- Python 3.11+ (incluso in FreeCAD 1.0)
- API FreeCAD: App, Gui, Part, Draft, Sketcher, TechDraw
- PySide6 (Qt) per dialog UI
- SVG per icone (max 10kb come da linee guida FreeCAD)
- Compatibilità: FreeCAD >= 1.0 (no versioni precedenti)
- Licenza: LGPL-2.1-or-later

### Struttura repository

```
PackagingWorkbench/
├── package.xml              # metadati Addon Manager FreeCAD
├── InitGui.py               # bootstrap GUI
├── Init.py                  # bootstrap no-GUI
├── PackagingWB.py           # classe workbench principale
├── commands/
│   ├── __init__.py
│   ├── cmd_fefco0201.py
│   ├── cmd_tray_lid.py
│   ├── cmd_tuck_end.py
│   └── cmd_unfold.py
├── objects/
│   ├── __init__.py
│   ├── base_box.py
│   ├── box_fefco0201.py
│   ├── box_tray_lid.py
│   └── box_tuck_end.py
├── utils/
│   ├── __init__.py
│   ├── unfold.py            # logica 3D -> 2D
│   └── die_lines.py         # generazione taglio/cordonatura
├── resources/icons/         # SVG icone
├── tests/
├── README.md                # bilingue IT/EN
├── LICENSE
├── CLAUDE.md
└── .gitignore
```

### Roadmap MVP (eseguire IN ORDINE, uno step alla volta)

- **Step 1 — Scheletro del workbench**: package.xml, InitGui.py, Init.py,
  PackagingWB.py, icona principale SVG, .gitignore, LICENSE, README bilingue,
  CLAUDE.md. TEST: il workbench appare nel selettore di FreeCAD.
- **Step 2 — Comando "Hello Box"**: comando registrato via
  `Gui.addCommand`, crea un `Part.Box` 200x150x100mm, toolbar + menu, icona
  dedicata.
- **Step 3 — Scatola FEFCO 0201 parametrica**: `Part::FeaturePython` con
  Proxy + ViewProvider. Proprietà: Length, Width, Height, Thickness,
  Allowance. Default 200x150x100mm, spessore 3mm, allowance 1mm. Geometria 3D
  scoppiata. `__getstate__`/`__setstate__`. Rigenerazione su cambio proprietà.
- **Step 4 — Fustella 2D associata**: piano di taglio automatico. Layer Draft:
  Cut (continua), Crease (tratteggiata), Perforation (puntinata). Export DXF +
  SVG (TechDraw).
- **Step 5 — Tray + Lid (FEFCO 0301)**: vassoio e coperchio separati.
- **Step 6 — Astuccio Tuck-End (FEFCO 0713)**: linguette interne.
- **Step 7 — Comando Unfold generico**: facce planari adiacenti, spigoli di
  piegatura, rotazione fino a complanarità.
- **Step 8 — Polish e distribuzione**: README con screenshot, docs/,
  versioning semantico (da 0.1.0), preparazione PR a FreeCAD-addons.

### Riferimenti tecnici FEFCO 0201 (RSC)

- Larghezza totale fustella = 2L + 2W + giunzione (~30mm)
- Altezza totale = H + W
- 4 pannelli laterali in sequenza: L, W, L, W + linguetta di giunzione
- Falde sopra/sotto larghe W/2 ciascuna
- Cordonature verticali tra ogni pannello
- Cordonature orizzontali separano corpo da falde
- Si lavora su dimensioni INTERNE; compensare spessore secondo direzione

### Convenzioni di codice

- Codice e commenti in inglese
- Documentazione utente bilingue italiano + inglese
- snake_case per funzioni/variabili, PascalCase per classi
- Docstrings Google style
- Linee max 100 caratteri
- Formatter: `black --line-length 100`; Linter: `ruff`
- Type hints dove sensato (non nelle API FreeCAD)

### Workflow git

- Branch: `feature/step-N-descrizione` (es. `feature/step-1-scaffold`)
- Conventional Commits in inglese (`feat(commands): ...`, `fix(unfold): ...`)
- Un branch + un set di commit per ogni Step
- NO git push automatici (solo commit locali)
- A fine di ogni Step: merge del branch in `main` localmente

### Cosa NON fare

- NO API deprecate (vecchio Drawing workbench, Part::Box obsoleto)
- NO dipendenze da workbench esterni (solo core FreeCAD 1.0)
- NO numpy/scipy se non strettamente necessario
- NO file binari grandi committati (.FCStd di test, screenshot > 500kb)
- NO logica pesante in InitGui.py (deve essere lazy-load)
- NON saltare step, NON implementare 3 step insieme
- NON installare pacchetti Python di sistema senza chiedere prima

### Riferimenti web utili

- https://wiki.freecad.org/Workbench_creation
- https://wiki.freecad.org/Scripted_objects
- https://wiki.freecad.org/Package_Metadata
- https://github.com/FreeCAD/FreeCAD-addons
- https://github.com/shaise/FreeCAD_SheetMetal
- https://www.fefco.org/technical-documents/code

---

## Status

- [x] **Step 1** — Scaffold (verified loading in FreeCAD 1.0.2)
- [x] **Step 2** — Hello Box command (verified: creates 200x150x100 Part::Box)
- [x] **Step 3** — FEFCO 0201 parametric box (verified: 72-face exploded shape, parametric, survives save/reload)
- [x] **Step 4** — 2D dieline generation (verified: Cut/Crease/Perforation groups, 14 cut + 6 crease lines, DXF export via importDXF.export)
- [x] **Step 5** — Tray + Lid (FEFCO 0301) (verified: 2 features 54 faces each, both dielines 20 cut + 8 crease)
- [x] **Step 6** — Tuck-End carton (FEFCO 0713) (verified: 78-face carton, dieline 28 cut + 12 crease)
- [~] Step 7 — Generic Unfold command (SKIPPED: GenerateDieline already dispatches across all box types)
- [x] **Step 8** — Polish & distribution (v1.0.0: flap-overlap fix, professional README, CHANGELOG, package.xml 1.0.0, tag v1.0.0)

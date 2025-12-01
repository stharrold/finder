---
type: claude-context
directory: .
purpose: Data organization repository for cataloging jewelry items
parent: null
sibling_readme: README.md
children: []
---

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is a data organization repository for cataloging jewelry items (primarily rings from Brilliant Earth). It stores product information, images, and order documentation.

## Directory Structure

```
finder/
└── YYYYMMDD_type_description/
    ├── input/    # Source materials (PDFs, images)
    └── output/   # Processed/generated files
```

## Naming Conventions

### Item Folders
Format: `YYYYMMDD_type_description`
- `YYYYMMDD`: Target or reference date
- `type`: Item category (e.g., `ring`)
- `description`: Hyphenated descriptors (e.g., `vintage-amethyst-pearl-gold`)

Example: `20251201_ring_vintage-amethyst-pearl-gold`

### Input Files
- Product PDFs: Full product page title from source (e.g., `Art Nouveau Amethyst Vintage Ring _ Giulia _ Brilliant Earth.pdf`)
- Product images: `ProductName_view.ext` where view is `top`, `side`, `hand_zi` (hand zoomed in), `hand_zo` (hand zoomed out)
- Order confirmations: `YYYYMMDD_source - subject.pdf`

## Branch Structure

```
main                           ← Production (tagged vX.Y.Z)
  ↑
develop                        ← Integration branch
  ↑
contrib/<gh-user>             ← Personal contribution branch
```

### Branch Protection Policy

**Protected branches** (merge via PR only):
- `main` - Production branch
- `develop` - Integration branch

**Editable branches** (direct commits allowed):
- `contrib/*` - Personal contribution branches

### PR Flow

All changes flow: `contrib/<user>` → `develop` → `main`

## Critical Guidelines

- **ALWAYS prefer editing existing files** over creating new ones
- **End on editable branch**: All work should end on `contrib/*` (never `develop` or `main`)
- **Follow naming conventions** for item folders and files

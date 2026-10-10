# Codebase Map

## Current status
This is a proposed target structure, not a statement that these files already exist. Create only the files needed for the current approved phase.

```text
CrisisSense/
├── AGENTS.md
├── CLAUDE.md
├── README.md
├── PRD.md
├── TASKS.md
├── PROGRESS.md
├── CODEBASE_MAP.md
├── CODING_STANDARDS.md
├── DATA_MODEL.md
├── ENVIRONMENT.md
├── SECURITY.md
├── GLOSSARY.md
├── UI_UX_SPEC.md
├── NON_FUNCTIONAL_REQUIREMENTS.md
├── CI_CD_RUNBOOK.md
├── OBSERVABILITY.md
├── OPEN_QUESTIONS.md
├── PROMPT_LIBRARY.md
├── ADRs/
├── backend/                  # Introduce when API phase is approved
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── schemas/
│   │   └── services/
│   └── tests/
├── research/                 # Notebooks/scripts and experiment documentation
│   ├── README.md
│   ├── data_manifests/       # Small manifests only, not datasets
│   ├── experiments/
│   └── reports/
├── frontend/                 # Optional, later phase
├── scripts/                  # Small reproducible utility scripts
├── .gitignore
└── pyproject.toml or requirements.txt
```

## Rules
- Do not create the whole tree in advance just to match the diagram.
- Prefer a single dependency manifest until complexity requires otherwise.
- Keep notebooks focused and ensure important experiment logic can be run reproducibly outside notebook-only hidden state.
- Store datasets and model weights outside Git.
- Update this map when the actual repository structure changes.
- `services/` above is a possible organization, not a mandate to create one service class per concept.

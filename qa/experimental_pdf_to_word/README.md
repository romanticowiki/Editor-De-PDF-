# EPDF PDF to Word experimental laboratory

This directory contains the isolated Fase 2A merge repair and the Fase 2B
vector-background prototype. Nothing here is imported by
`backend/app/services/pdf_to_word.py` or by the production API route.

Generate anonymous fixtures:

```powershell
@'
from pathlib import Path
from qa.experimental_pdf_to_word.fixtures import generate_all
generate_all(Path($env:TEMP) / "epdf-phase2a-fixtures")
'@ | backend\.venv\Scripts\python.exe -
```

Run the prototype:

```powershell
backend\.venv\Scripts\python.exe qa\experimental_pdf_to_word\run_experiment.py `
  --pdf input.pdf `
  --docx experimental.docx `
  --json experimental.json `
  --reconcile-row-heights `
  --recover-backgrounds
```

Run the anonymous baseline / Fase 2A / Fase 2B matrix:

```powershell
backend\.venv\Scripts\python.exe qa\experimental_pdf_to_word\run_phase2b_matrix.py `
  --output-dir tmp\phase2b\matrix `
  --json qa\phase2b\synthetic-matrix.json
```

Run the unmodified pdf2docx path with the same measurement harness:

```powershell
backend\.venv\Scripts\python.exe qa\experimental_pdf_to_word\run_experiment.py `
  --pdf input.pdf `
  --docx baseline.docx `
  --json baseline.json `
  --baseline
```

Trace layout-to-DOCX loss:

```powershell
backend\.venv\Scripts\python.exe qa\experimental_pdf_to_word\trace_loss.py `
  --pdf input.pdf `
  --docx baseline.docx `
  --json loss-trace.json
```

The optional `--suppress-stream-inside-lattice` branch is retained only to
reproduce the rejected selective-stream experiment. It did not change the
problematic parse tree and is not part of the recommended prototype.

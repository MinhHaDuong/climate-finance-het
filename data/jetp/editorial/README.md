# Editorial dossiers

Markdown is the human reading/editing layer. Ledger tables are in the
[storage contract](../../../docs/jetp-ledger-storage.md).

Prose owns explanation, interpretation and context, never numbers: front
matter holds join IDs, review state and referenced statements, not a
project's operator, amount or stage. A narrative may quote a dated statement
with its reference, but prose is never an input to an aggregate. When a
ledger observation changes, the release check lists the narratives that
depend on it for review, so a contradicting narrative is not published
silently. A missing dossier is acceptable; an unsupported narrative claim is
not. (Carried from the storage note of 2026-09-13, deleted by ticket 1701.)

| Folder | Filename | Content |
|---|---|---|
| `countries/` | `ZAF.md`, `IDN.md`, `VNM.md`, `SEN.md` | Country context and interpretation |
| `projects/` | `<project_id>.md` | Explanation of an existing canonical project |
| `editions/` | `<edition_id>.md` | What changed, corrections and evidence gaps |
| `templates/` | Reusable Markdown templates | Not published as dossiers |

Create a dossier from its template when there is reviewed prose to add. Drafts
remain explicitly draft. `reviewed_on` means editorial review, not event date.
Empty source/claim lists mean no referenced evidence yet, not verified absence.
Front matter is a proposed publication contract for 0726, not a parser already
implemented. Its validator must reject unknown IDs before release.

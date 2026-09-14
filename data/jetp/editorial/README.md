# Editorial dossiers

Markdown is the human reading/editing layer. See
[storage contract](../../../docs/jetp-storage.md) for fact ownership and publication.

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

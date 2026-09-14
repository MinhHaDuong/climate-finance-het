# Revision 5 response: display identity

14 September 2026. Resolves A4-1 from the [independent revision 4 review](astra-revision4.md).

[Section 8 of the design](../jetp-backend-design.md#8-full-traceability-to-publications)
now uses `(release_id, display_id)` as the occurrence identity for website and
manuscript outputs. Publication, artifact, data locator and role may repeat.
Routes and stable rendered-instance locators retain each rendered location,
including repeated components on one page. Reverse traversal enumerates display
IDs, so shared data does not collapse distinct displays.

The JSON example now reuses the same field and role on two routes. Acceptance
cases require preserving both displays, preserving repeated instances on one
page, and rejecting duplicate display IDs across the entire release. The same
cases apply to manuscript occurrences.

This repairs the design contract only. The schema and traversal acceptance cases
remain implementation work. The independent report and reviewed-input manifest
are preserved as historical evidence; this response is not a new independent review.

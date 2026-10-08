# Batch models for mass processing

Author decision, 2026-10-08:

> Use Luna and Haiku at batch price for mass processing like summarizing,
> labeling, recognizing.

Prefer Luna and Haiku through their providers' Batch APIs for large-volume
summarization, labeling, recognition, and similar bounded processing tasks.
Validate the model and prompt on the actual task before a production run;
escalate cases that need stronger judgment rather than defaulting the whole
population to a more expensive model. Keep the approved budget, exact model
and prompt versions, native responses, and usage provenance.

This preference does not certify a particular screening method. During the
current corpus run, Haiku completed Stage 1, while Luna's original Stage 2
prompt failed explicit CDM cases. A revised prompt is being tested with
three separate ICF facets and mechanism aliases; production approval is
still pending that assessment.

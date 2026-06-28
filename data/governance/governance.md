# Data Governance & Records Schedule (CONFIDENTIAL — internal control document)

> This schedule governs which documents may surface in the employee knowledge assistant.
> It is an internal control artifact: it shapes retrieval but is **never shown to end users
> or sent to the answering model**. Each clause is compiled to a machine-applicable
> PREDICATE policy in `policies.json` (the only form the runtime consumes). Predicates
> reference document **attributes**, not IDs, so they stay correct as the corpus changes.

## §2 Classification & Personal Data
- **§2.1** Documents classified **Restricted** must never be surfaced in general retrieval.
- **§2.2** Documents containing **personal data (PII)** must not be surfaced to general queries.

## §3 Records Lifecycle
- **§3.1** **Deprecated** or **superseded** documents must not be surfaced as guidance.
- **§3.2** The **current** authoritative version is preferred over other versions.

## §4 Jurisdiction
- **§4.1** Regional editions that do not match the query's jurisdiction context are demoted.

## §5 Legal Holds
- **§5.1** Records under an **active legal hold** must be withheld from knowledge retrieval.

---
*Compilation note:* §2.1, §2.2, §3.1, §5.1 are **hard** constraints (exact exclusion, applied
unconditionally); §3.2 and §4.1 are **soft** preferences (score adjustments).

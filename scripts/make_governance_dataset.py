#!/usr/bin/env python
"""
Generate a NON-card governance dataset: a corporate knowledge base governed by a
hidden Data Governance & Records Schedule.

Demonstrates that Asymmetric Visibility is a general retrieval property. Items are internal
documents with governance attributes; a hidden schedule compiles to attribute-PREDICATE
policies that shape retrieval without ever being shown to the user/LLM.

Design notes (v2 — harder relevance):
  * Each department TOPIC has 3 distinct SUB-TOPICS (lexically overlapping but answering
    different questions), so retrieval must discriminate within a topic — relevance is not
    at ceiling.
  * Each sub-topic has an authoritative `current` doc plus a must-exclude variant
    (deprecated / restricted+PII / legal-hold), and some have a regional edition.
  * DISTRACTOR documents (unrelated topics) enlarge and confuse the corpus.
  * Relevance gold = the SPECIFIC sub-topic's docs (governance-independent).

Writes data/governance/{documents.json, queries.json, policies.json, governance.md}.
Run: python scripts/make_governance_dataset.py
"""
import json
from pathlib import Path

OUT = Path(__file__).parent.parent / "data" / "governance"

# topic -> list of (subtopic_key, query, content_sentence)
TOPICS = {
    "incident_response": [
        ("report", "How do I report a security incident?",
         "Reporting a security incident: open a ticket with the Security Operations Center, "
         "record the time of detection, and notify your manager."),
        ("escalate", "How do I escalate a critical security breach?",
         "Escalating a security breach: use the severity matrix, page the on-call incident "
         "commander for Sev-1, and convene the response bridge."),
        ("evidence", "How do I preserve evidence after a security incident?",
         "Preserving evidence after a security incident: do not power off affected hosts, "
         "capture memory and disk images, and maintain chain of custody."),
    ],
    "parental_leave": [
        ("eligibility", "Am I eligible for parental leave?",
         "Parental leave eligibility: minimum tenure, covered family events, and required "
         "documentation for maternity and paternity leave."),
        ("duration", "How much parental leave pay and time do I get?",
         "Parental leave duration and pay: weeks of leave, pay continuation percentage, and "
         "interaction with statutory benefits."),
        ("return", "How do I return to work after parental leave?",
         "Returning to work after parental leave: notice to manager, phased return options, "
         "and reinstatement of benefits."),
    ],
    "expense_reimbursement": [
        ("submit", "How do I submit an expense reimbursement claim?",
         "Submitting an expense claim: enter the report in the portal, attach receipts, and "
         "route to your approver."),
        ("receipts", "What receipts are required for expense claims?",
         "Receipt requirements for expenses: itemized receipts above the threshold, currency "
         "conversion notes, and missing-receipt affidavits."),
        ("perdiem", "What is the travel per diem limit?",
         "Travel per-diem limits: daily meal and incidental caps by city tier and partial-day "
         "proration rules."),
    ],
    "data_retention": [
        ("periods", "How long must we retain financial records?",
         "Records retention periods: minimum retention by record category including financial, "
         "HR, and contractual records."),
        ("disposal", "What is the records disposal procedure?",
         "Records disposal procedure: eligibility review, approval to destroy, secure "
         "destruction method, and disposal log."),
        ("hold", "What happens to records under a legal hold?",
         "Legal hold handling: suspend disposal, identify custodians, and preserve records "
         "until the hold is released."),
    ],
    "vpn_access": [
        ("setup", "How do I request and set up remote VPN access?",
         "Requesting VPN access: submit the access request, install the VPN client, and import "
         "the connection profile."),
        ("mfa", "How do I enroll in VPN multi-factor authentication?",
         "VPN multi-factor authentication enrollment: register an authenticator app, bind your "
         "device, and test a challenge."),
        ("trouble", "I can't connect to the VPN, how do I troubleshoot?",
         "VPN troubleshooting: check credentials and MFA, reset the client, verify network, "
         "and review common connection error codes."),
    ],
    "visitor_badges": [
        ("prereg", "How do I pre-register a visitor for a badge?",
         "Visitor pre-registration: enter visitor details in advance, select the host, and "
         "choose the access window."),
        ("signin", "What is the visitor sign-in process at reception?",
         "Visitor sign-in at reception: present ID, print the badge, and acknowledge the "
         "safety briefing."),
        ("escort", "Do visitors need an escort on site?",
         "Visitor escort rules: escort requirements by area sensitivity and unescorted-access "
         "exceptions."),
    ],
}

# must-exclude variant assigned to each sub-topic, cycled for coverage
BAD_CYCLE = [
    ("deprecated", {"status": "deprecated", "classification": "internal", "contains_pii": False, "legal_hold": False, "tag": "(2019, deprecated)"}),
    ("restricted", {"status": "current", "classification": "restricted", "contains_pii": True, "legal_hold": False, "tag": "(restricted, contains PII)"}),
    ("hold",       {"status": "current", "classification": "confidential", "contains_pii": False, "legal_hold": True, "tag": "(legal hold)"}),
]
# sub-topics that also get a regional edition (index -> region)
REGION_AT = {2: "EU", 5: "US", 8: "EU"}

DISTRACTORS = [
    ("Office Coffee Service", "Office coffee and pantry service: machine locations, restocking schedule, and barista hours."),
    ("Parking Lot Map", "Campus parking: lot assignments, EV charging stalls, and overflow parking guidance."),
    ("Gym Membership Perk", "On-site gym and wellness perk: hours, class booking, and locker assignment."),
    ("Cafeteria Menu Policy", "Cafeteria menu rotation, dietary labeling, and allergen disclosure."),
    ("Desk Booking System", "Hot-desk booking: reserve a desk, check-in window, and neighborhood zones."),
    ("Mail Room Hours", "Mail room: package pickup hours, courier drop-off, and oversized item handling."),
    ("Recycling Guidelines", "Recycling and waste sorting: bin colors, compost rules, and e-waste days."),
    ("Conference Room AV", "Conference room AV: connecting a laptop, booking a room, and reporting AV faults."),
    ("Company Swag Store", "Internal swag store: ordering branded merchandise and redemption points."),
    ("Wellness Webinars", "Monthly wellness webinars: schedule, registration, and recordings."),
]


def build_documents():
    docs = []
    idx = 0
    for topic, subs in TOPICS.items():
        for (skey, _query, content) in subs:
            base = f"doc_{topic}_{skey}"
            # authoritative current GLOBAL
            docs.append({
                "id": f"{base}_current", "title": f"{content.split(':')[0]} (current)",
                "text": f"{content} Status: current authoritative version.",
                "topic": topic, "subtopic": skey, "status": "current",
                "classification": "internal", "jurisdiction": "GLOBAL",
                "contains_pii": False, "legal_hold": False,
            })
            # must-exclude variant (cycled)
            bsuf, b = BAD_CYCLE[idx % len(BAD_CYCLE)]
            docs.append({
                "id": f"{base}_{bsuf}", "title": f"{content.split(':')[0]} {b['tag']}",
                "text": f"{content} {b['tag']}",
                "topic": topic, "subtopic": skey, "status": b["status"],
                "classification": b["classification"], "jurisdiction": "GLOBAL",
                "contains_pii": b["contains_pii"], "legal_hold": b["legal_hold"],
            })
            # optional regional edition
            if idx in REGION_AT:
                region = REGION_AT[idx]
                docs.append({
                    "id": f"{base}_{region.lower()}", "title": f"{content.split(':')[0]} ({region} edition)",
                    "text": f"{content} {region} regional edition.",
                    "topic": topic, "subtopic": skey, "status": "current",
                    "classification": "internal", "jurisdiction": region,
                    "contains_pii": False, "legal_hold": False,
                })
            idx += 1
    # distractors
    for n, (title, body) in enumerate(DISTRACTORS):
        docs.append({
            "id": f"doc_distractor_{n:02d}", "title": title, "text": f"{title}. {body}",
            "topic": "_distractor", "subtopic": f"d{n}", "status": "current",
            "classification": "public", "jurisdiction": "GLOBAL",
            "contains_pii": False, "legal_hold": False,
        })
    return docs


# Indirect, natural-language queries (NOT verbatim restatements of the doc), so the
# reranker must genuinely discriminate the right sub-topic among lexical neighbours.
INDIRECT = {
    ("incident_response", "report"): "I think I clicked a phishing link and my account looks wrong — what do I do first?",
    ("incident_response", "escalate"): "There's a major suspected attack causing an outage; who needs to be paged right now?",
    ("incident_response", "evidence"): "My work laptop might be compromised — should I power it off or leave it running?",
    ("parental_leave", "eligibility"): "We're expecting a baby soon — do I qualify for leave and what do I need to provide?",
    ("parental_leave", "duration"): "How many weeks off do new parents get and is it fully paid?",
    ("parental_leave", "return"): "Coming back after having a child — how do I phase in and restore my benefits?",
    ("expense_reimbursement", "submit"): "I paid for a client dinner out of pocket — how do I get my money back?",
    ("expense_reimbursement", "receipts"): "Do I need to keep the paper slips for small purchases on a trip?",
    ("expense_reimbursement", "perdiem"): "What's the daily food allowance when I'm traveling for work?",
    ("data_retention", "periods"): "How many years do we have to keep old invoices and signed contracts?",
    ("data_retention", "disposal"): "We have boxes of old files — how do we get approval to shred them?",
    ("data_retention", "hold"): "Legal told us not to delete anything for a case — what does that mean for our files?",
    ("vpn_access", "setup"): "I'm working from home and can't reach internal systems — how do I get connected?",
    ("vpn_access", "mfa"): "It's asking for a second factor when I connect remotely — how do I set that up?",
    ("vpn_access", "trouble"): "My remote connection keeps dropping and won't authenticate — how do I fix it?",
    ("visitor_badges", "prereg"): "A client is coming next week — how do I arrange a badge for them ahead of time?",
    ("visitor_badges", "signin"): "What does a guest do when they arrive at the front desk?",
    ("visitor_badges", "escort"): "Can a guest walk around the building alone or do I need to stay with them?",
}
# Region-context variants (contain a jurisdiction cue so §4.1 triggers).
REGION_QUERIES = {
    ("incident_response", "evidence"): ("In our EU office, should I shut down a possibly-hacked laptop?", "EU"),
    ("parental_leave", "return"): ("I'm in the US office — how do I phase back after parental leave?", "US"),
    ("expense_reimbursement", "perdiem"): ("What's the daily meal allowance for travel in Europe (EU)?", "EU"),
}


def build_queries(docs):
    sub_docs = {}
    for d in docs:
        if d["topic"] != "_distractor":
            sub_docs.setdefault((d["topic"], d["subtopic"]), []).append(d["id"])

    qs, qid = [], 1
    idx = 0
    for topic, subs in TOPICS.items():
        for (skey, _verbatim, _content) in subs:
            gold = sorted(sub_docs[(topic, skey)])
            base = f"doc_{topic}_{skey}"
            qs.append({"id": f"gq{qid:03d}", "query": INDIRECT[(topic, skey)],
                       "topic": topic, "subtopic": skey, "region": None,
                       "expected_topic_docs": gold,
                       "authorized_doc": f"{base}_current", "difficulty": "medium"})
            qid += 1
            if (topic, skey) in REGION_QUERIES:
                rq, region = REGION_QUERIES[(topic, skey)]
                qs.append({"id": f"gq{qid:03d}", "query": rq, "topic": topic, "subtopic": skey,
                           "region": region, "expected_topic_docs": gold,
                           "authorized_doc": f"{base}_{region.lower()}", "difficulty": "hard"})
                qid += 1
            idx += 1
    return qs


POLICIES = [
    {"id": "GOV-2.1", "source": "Data Governance Schedule §2.1 Classification",
     "rule": "Documents classified Restricted must never be surfaced in general retrieval.",
     "action": "EXCLUDE", "tier": "hard", "trigger": {"keywords": []},
     "predicate": {"field": "classification", "op": "eq", "value": "restricted"}},
    {"id": "GOV-2.2", "source": "Data Governance Schedule §2.2 Personal Data",
     "rule": "Documents containing personal data (PII) must not be surfaced to general queries.",
     "action": "EXCLUDE", "tier": "hard", "trigger": {"keywords": []},
     "predicate": {"field": "contains_pii", "op": "eq", "value": True}},
    {"id": "GOV-3.1", "source": "Records Schedule §3.1 Lifecycle",
     "rule": "Deprecated or superseded documents must not be surfaced as guidance.",
     "action": "EXCLUDE", "tier": "hard", "trigger": {"keywords": []},
     "predicate": {"field": "status", "op": "in", "value": ["deprecated", "superseded"]}},
    {"id": "GOV-5.1", "source": "Legal Holds §5.1",
     "rule": "Records under active legal hold must be withheld from knowledge retrieval.",
     "action": "EXCLUDE", "tier": "hard", "trigger": {"keywords": []},
     "predicate": {"field": "legal_hold", "op": "eq", "value": True}},
    {"id": "GOV-3.2", "source": "Records Schedule §3.2 Currency",
     "rule": "Prefer the current authoritative version of a document.",
     "action": "BOOST", "tier": "soft", "weight": 5.0, "trigger": {"keywords": []},
     "predicate": {"field": "status", "op": "eq", "value": "current"}},
    {"id": "GOV-4.1-EU", "source": "Jurisdiction §4.1 (EU context)",
     "rule": "For EU-context queries, demote non-EU regional editions.",
     "action": "DEMOTE", "tier": "soft", "weight": 5.0,
     "trigger": {"keywords": ["germany", "eu", "europe", "gdpr", "(eu)"]},
     "predicate": {"field": "jurisdiction", "op": "in", "value": ["US", "APAC"]}},
    {"id": "GOV-4.1-US", "source": "Jurisdiction §4.1 (US context)",
     "rule": "For US-context queries, demote non-US regional editions.",
     "action": "DEMOTE", "tier": "soft", "weight": 5.0,
     "trigger": {"keywords": ["(us)", " usa", "united states"]},
     "predicate": {"field": "jurisdiction", "op": "in", "value": ["EU", "APAC"]}},
]

GOVERNANCE_MD = """# Data Governance & Records Schedule (CONFIDENTIAL — internal control document)

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
"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    docs = build_documents()
    queries = build_queries(docs)
    (OUT / "documents.json").write_text(json.dumps(docs, indent=2), encoding="utf-8")
    (OUT / "queries.json").write_text(json.dumps(queries, indent=2), encoding="utf-8")
    (OUT / "policies.json").write_text(json.dumps(POLICIES, indent=2), encoding="utf-8")
    (OUT / "governance.md").write_text(GOVERNANCE_MD, encoding="utf-8")
    from collections import Counter
    print(f"Wrote {len(docs)} documents ({sum(1 for d in docs if d['topic']=='_distractor')} distractors), "
          f"{len(queries)} queries, {len(POLICIES)} policies to {OUT}")
    print("status:", dict(Counter(d["status"] for d in docs)))
    print("classification:", dict(Counter(d["classification"] for d in docs)))
    must_excl = sum(1 for d in docs if d["classification"] == "restricted" or d["contains_pii"]
                    or d["status"] in ("deprecated", "superseded") or d["legal_hold"])
    print(f"must-exclude docs: {must_excl}")


if __name__ == "__main__":
    main()

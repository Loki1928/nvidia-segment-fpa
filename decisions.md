# Design Decisions Log

Every meaningful design choice made while building this project, with the reasoning. Each entry captures the decision, the alternative considered, the trade-off accepted, and an interview talking point.

---

## Decision 1 — Geographic basis change (Path A)

**Context:** NVIDIA changed geographic reporting basis in Q3 FY26 from "bill-to location" (where the invoice goes) to "customer HQ location" (where the customer is headquartered). The Q3 10-Q recast prior periods on the new basis but only for the comparative column shown — not for all prior quarters individually.

**Decision:** Kept Q1 and Q2 FY26 on the old bill-to basis (with Singapore broken out separately, ~$9B and $10B per quarter). Q3 FY26 on the new customer-HQ basis (Singapore collapsed into US). FY25 Q1 and Q2 on old basis; FY25 Q3 on new basis (recast in Q3 10-Q comparison column).

**Alternative considered:** Path B — find restated Q1 and Q2 numbers in the FY26 10-K Segment Information note and replace the old-basis rows. Rejected because the FY26 10-K does not break out quarterly geography by region on the new basis (only annual totals are restated).

**Trade-off accepted:** FY26 quarterly geography does not reconcile cleanly to annual geography because the bases differ. Documented as a known reconciliation gap. Tagged in the data via the BasisKey column in FactGeography.

**Interview talking point:** When asked "how do you handle a real-world disclosure change mid-year?", the answer is: capture the change explicitly in the data model (DimBasis), don't paper over it. Hidden assumptions become hidden bugs.

---

## Decision 2 — "All Other" segment row

**Context:** Q1 FY26 10-Q disclosed "All Other" (corporate unallocated cost — primarily stock-based compensation and corporate overhead) as a separate row in the Operating Income by Reportable Segments table, totaling −$2,056M. Q2 and Q3 10-Qs dropped that row from the segment table display but the underlying cost still flows through consolidated operating income.

**Decision:** Maintained the Q1 disclosure structure consistently across all 8 quarters in segment_quarterly. For Q2/Q3/Q4 (and FY25 equivalents), derived All Other by computing (consolidated OpInc from the income statement) − (segment-only OpInc from the segment table). Made All Other a third segment row (`SegmentKey = 'OTH'`) in DimSegment with Revenue = 0 and OperatingIncome = the negative corporate unallocated number.

**Alternative considered:** Push the corporate cost down into the segment OSI lines proportionally (matching what the annual 10-K appears to do). Rejected because (a) NVIDIA's internal allocation methodology is not disclosed, and (b) the annual approach loses information that's useful for analysis (e.g. "how much is corporate cost growing vs segment cost").

**Trade-off accepted:** Slight schema asymmetry between segment_annual (no All Other row) and segment_quarterly (All Other row per period). Reconciled in the ETL validation suite (Check 1).

**Interview talking point:** Every quarter of segment_quarterly OpInc ties to NVIDIA's reported consolidated operating income to the dollar — $130,387M for FY26 and $81,453M for FY25.

---

## Decision 3 — Star schema with natural TEXT primary keys

**Context:** SQLite database design. Could use auto-incrementing integer surrogate keys (the textbook "best practice") or natural text keys derived from the business identifiers.

**Decision:** Used natural TEXT primary keys throughout:
- PeriodKey: 'FY26Q1', 'FY26', etc.
- SegmentKey: 'CN' (Compute & Networking), 'GFX' (Graphics), 'OTH' (All Other)
- EndMarketKey: 'DC', 'DC_COMP', 'DC_NET', 'GAMING', 'PROVIZ', 'AUTO', 'OEM'
- GeographyKey: 'US', 'SG', 'TW', 'CN_HK', 'OTH'
- BasisKey: 'BILL_TO', 'CUST_HQ'
- ScenarioKey: 'ACT', 'BASE', 'BULL', 'BEAR'

**Alternative considered:** Integer surrogate keys with a `name` column on each dimension. Standard data warehouse pattern.

**Reasoning:** Natural keys make hand-written SQL dramatically more readable. `WHERE SegmentKey = 'CN'` is clearer than `WHERE SegmentKey = 2`. At this scale (8 quarters, 3 segments, 7 end-markets, 5 geographies, 2 bases, 4 scenarios), there is no performance difference. The trade-off — that any rename of a business term requires updating fact tables — is acceptable for analytical data that doesn't get renamed.

**Interview talking point:** When asked about schema choices, this is a real opinion to hold: "For analytical workloads at small to mid scale where queries are written by hand, natural keys win on readability. I'd switch to surrogate keys at warehouse scale where ETL automation matters more than hand-writeability."

---

## Decision 4 — DimBasis as a separate dimension

**Context:** Could have buried the geographic basis change in a Notes column on FactGeography, or as a flag column directly on each row.

**Decision:** Created DimBasis as a proper dimension table with two rows ('BILL_TO' and 'CUST_HQ'), and FactGeography includes BasisKey as part of its composite primary key.

**Reasoning:** The basis change isn't a side note — it's a real business event that affects how the geography numbers should be compared across periods. Making BasisKey a first-class dimension lets queries filter on it explicitly:
- `WHERE BasisKey = 'CUST_HQ'` for current-basis-only analysis
- `GROUP BY BasisKey` to see the size of the gap between bases
- A future restatement of Q1/Q2 to the new basis can be loaded as additional rows tagged with the new basis without touching the original rows

**Interview talking point:** Demonstrates that data architecture should encode business reality, not hide it. A common junior mistake is to silently overwrite old-basis numbers with new-basis numbers and lose the audit trail.

---

## Decision 5 — DimPeriod handles both quarterly and annual granularity

**Context:** Could have built two separate sets of fact tables (FactSegmentQuarterly + FactSegmentAnnual) or one set of fact tables with a granularity-aware DimPeriod.

**Decision:** Single set of fact tables. DimPeriod has rows for both quarters ('FY26Q1' etc.) and annual ('FY26' etc.) with a `Granularity` column ('Quarter' or 'Annual') to distinguish them.

**Reasoning:** Avoids the double-counting trap when a user queries the fact table without filtering. The `Granularity` column makes the intent explicit — `WHERE Granularity = 'Quarter'` for quarterly analysis, or `WHERE Granularity = 'Annual'` for annual rollups. Cleaner than maintaining two schemas in parallel and keeping them in sync.

**Interview talking point:** When asked about handling mixed granularity in a fact table: model it as a dimension attribute, not as separate tables. Easier to query, easier to maintain, harder to accidentally double-count.

---

## Decision 6 — DimScenario included from day one

**Context:** Week 3 of this project will add Bull/Base/Bear forecast scenarios. Could have added DimScenario then.

**Decision:** Built DimScenario into the schema from the start, with 'ACT' (actual) as the only scenario populated initially. ScenarioKey is part of every fact table's primary key.

**Reasoning:** Adding a new dimension to a fact table after data is loaded is painful — every existing row needs to be tagged retroactively, and any code or query that hits the fact table needs to be updated. Building the slot in from day one costs almost nothing and saves a refactor later.

**Interview talking point:** Most production data warehouse rework comes from new dimensions being added retroactively. Building hooks early is cheap.

---

## Decision 7 — Sub-lines flagged in DimEndMarket rather than stored in a separate table

**Context:** NVIDIA's end-market disclosure shows Data Center as a parent line, then breaks it into Compute and Networking as sub-lines. If you sum all end-market lines naively you double-count the Data Center number.

**Decision:** Stored Compute and Networking as separate rows in DimEndMarket with `IsSubline = 1` and `ParentEndMarket = 'DC'`. Total revenue queries filter `WHERE IsSubline = 0`.

**Alternative considered:** Two separate tables — one for top-level end markets, one for Data Center sub-lines. Rejected because it makes joins more complex and the sub-line vs parent distinction is a property of the dimension, not a separate entity.

**Trade-off accepted:** Every query that sums end-market revenue must remember the filter. Mitigated by documenting this clearly and by Reconciliation Check 3 (sub-lines sum to parent), which would fail loudly if the rule were ever violated.

**Interview talking point:** For shallow hierarchies (1–2 levels), a flag column with a parent reference is sufficient. For deeper hierarchies (4+ levels), a separate hierarchy table with closure tables is appropriate.

---

## Decision 8 — Q4 geography intentionally not derived

**Context:** Segment and end-market FY25Q4 and FY26Q4 were derived by subtraction (Annual − Q1+Q2+Q3) in Week 1, because 10-K segment and end-market tables present consistent disclosure formats across all quarters and the annual roll-up. Geography is structurally different: the FY26 10-K restated annual geography to the new customer-HQ basis (Singapore collapsed into US), while the Q1 and Q2 10-Qs of FY26 and all of FY25 are on the old bill-to basis (Singapore broken out separately).

**Decision:** Did not derive FY25Q4 or FY26Q4 geography by subtraction. FactGeography covers 6 quarterly periods (FY25 Q1–Q3, FY26 Q1–Q3) plus 3 annual periods, for 40 rows total: 28 quarterly + 12 annual.

**Reasoning:** Deriving Q4 geography by Annual (customer-HQ basis, 4 lines, no Singapore) minus Q1+Q2+Q3 (mixed: Q1+Q2 bill-to with Singapore broken out, Q3 customer-HQ without Singapore) would mix two reporting bases within a single derivation. The result would not be a Q4 anything — it would be an arithmetic artifact. Real Q4 geography on either basis is not recoverable from publicly disclosed data, so the right call is to leave the gap visible.

**Alternative considered:** Drop FY25Q4 and FY26Q4 rows from DimPeriod entirely, so the schema is internally symmetric. Rejected because that would also lose the segment and end-market Q4 data, which IS validly derived (segment and end-market disclosures use consistent basis across quarters and annual).

**Trade-off accepted:** FactGeography is incomplete relative to FactSegment and FactEndMarket for Q4 periods. Reconciliation Check 4 in load_data.py only runs over periods where geography data exists, and reports 9 of 11 periods reconciling, making the gap visible rather than hidden.

**Interview talking point:** When asked "why is your geography incomplete?", the answer is: it's not incomplete by accident, it's a methodologically constrained choice. The right way to handle a mid-year disclosure basis change is to flag what can and can't be reconstructed, not to manufacture numbers that look complete but aren't real.

---

## Open questions / decisions deferred

These are decisions not yet made — they'll come up in later weeks of the project.

- **DCF discount rate methodology** — Week 3. Bottom-up WACC or treasury+ERP approach? Defer.
- **Forecast horizon length** — Week 3. Initial plan is 2 years; confirm before building.
- **Power BI vs Looker Studio** — Week 4. Power BI is on the resume so default to it. Looker Studio is free and might be useful for a public-facing demo URL.
- **README screenshot vs README GIF** — Week 4. A short GIF of dashboard navigation is more impressive than a static screenshot but takes more effort to produce.

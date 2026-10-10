# Proposed data-quality policy (Phase 2 draft)

No irreversible cleaning has been applied. Approval is required before Phase 3.

- Preserve the raw CSV unchanged and record its SHA-256 checksum.
- Standardize headers/string whitespace only on a working copy and retain mappings.
- Normalize only reviewed missing tokens.
- Parse dates and numeric fields explicitly; report conversion failures.
- For the observed data, accept `Datetime` in either
  `YYYY-MM-DD HH:MM:SS` or `YYYY-MM-DD` form, and accept `Date` in
  `DD/MM/YY` form. Preserve the original values in the clean output.
- Separate exact duplicate rows from repeated measurements.
- Flag plausible outliers; quarantine only malformed/impossible records with reason codes.
- Do not choose an AQI formula, forecast target, station key, or imputation rule until data meaning and source standard are confirmed.
- Retain before/after counts, nulls, conversions, duplicates, outliers, and rejection reasons.

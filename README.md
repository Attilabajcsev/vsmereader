# VSME iXBRL Uploader — MVP

Minimal web app to upload an EFRAG VSME Inline XBRL report, track validation, view basic metadata and extracted datapoints, and download both the original file and the extracted JSON.

## What you can do
- Upload a report: single `.xhtml` VSME iXBRL file or a `.zip` IXDS.
- See status: Processing → Validated / Failed with a clear reason.
- Browse your uploads: per-user list with Entity, Reporting Period, Status, and Created Date.
- Open a report: view metadata, validation summary, and a table of extracted facts.
- Filter facts by keyword and paginate results.
- Download the original iXBRL and the extracted JSON.

## Users & access
- Per-user workspace: you only see your own uploads and data.
- Authentication is already implemented and remains unchanged (JWT in HttpOnly cookies, refresh/verify, and optional Google OAuth). We are building on top of the existing login and session handling.

## Accepted files
- One file per upload.
- Types: `.xhtml` VSME iXBRL or `.zip` containing an Inline XBRL Document Set (IXDS).
- Basic size/type checks; one report per upload.

## Screens
### 1) Upload
- File picker with brief guidance (accepted types, size limit) and an Upload button.
- After submit: inline progress “Processing…”, then “Validated” or “Failed”.
- On success: link/button to “View report”.
- On failure: short human-readable reason and a “Try again” action.

### 2) Reports List
- Table of your uploads with: Entity, Reporting Period, Status (Processing / Validated / Failed), Created Date.
- Keyword filter (matches Entity or Period).
- Row click opens Report Detail.

### 3) Report Detail
- Header shows: Entity, Reporting Period, Taxonomy Version (text), Created Date, Status.
- Validation summary box: “Validated” or “Failed” with brief key messages.
- Facts table (50 rows/page):
  - Columns: Concept (QName or label), Value (truncated if long), Datatype, Unit (if any), Context (period/instant).
  - Keyword filter (matches Concept or Value text).
  - Pagination (e.g., 50 rows/page).
- Download buttons:
  - “Download original iXBRL”
  - “Download extracted JSON”

## States & messages
- Processing → Validated / Failed.
- Common failures: invalid file type/structure, file too large, not a VSME iXBRL/IXDS.
- Clear, short error messages only (no stack traces).

## Empty states
- No uploads yet: “You haven’t uploaded any reports.” with “Upload your first report” CTA.
- No facts match filter: “No datapoints match your search.”

## Non-goals (MVP)
- No editing of facts or metadata.
- No analytics, charts, or cross-report comparisons.
- No bulk upload.
- No team/org sharing or roles beyond basic per-user isolation.

## Success criteria
- A valid upload appears in the list with correct Entity/Period and “Validated” status.
- Report Detail shows a readable validation summary and a populated facts table.
- Users can download both the original iXBRL and the extracted JSON.
- Failed uploads show a clear reason and do not appear as validated.

## Run locally (development)
This project uses Docker for local development with separate frontend and backend services.

1. From the repository root, start the stack:
   - `docker-compose up`
2. Sign in using the existing login flow (JWT cookies / optional Google OAuth).
3. Upload a VSME iXBRL report and follow the status through to validation.

Notes:
- We build on the existing authentication, login, and JWT cookie handling already present in the codebase. No changes required to use the MVP features.

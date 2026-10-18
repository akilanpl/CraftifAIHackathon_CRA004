# Final product acceptance

**239 backend tests and 89 frontend tests passed.** TypeScript and the production build passed. Real CPU-worker source integration tests were enabled.

## Page and viewport matrix

| Page | 1600×900 | 1920×1080 | 1366×768 | 390×844 |
|---|---|---|---|---|
| Overview | PASS | PASS | PASS | PASS |
| Recorded Monitoring | PASS | PASS | PASS | PASS |
| Incident Center | PASS | PASS | PASS | PASS |
| Zone Management | PASS | PASS | PASS | PASS |
| Analytics | PASS | PASS | PASS | PASS |
| Model Performance | PASS | PASS | PASS | PASS |
| AI Camera Monitor | PASS | PASS | PASS | PASS |
| Integration | PASS | PASS | PASS | PASS |

All 32 rendered layouts were captured and measured. All eight desktop page screenshots and the new pages' mobile screenshots were visually inspected. Normal browser console warnings/errors were empty. Recorded boxes had zero PTS error and less than 0.0001 px projected geometry drift in the measured views.

## Functional acceptance

| Workflow | Result | Executed evidence |
|---|---|---|
| Warehouse V2 | PASS | 254 frames, 522 person observations, 6 tracker IDs; original two incidents and polygon retained. |
| CPU virtual video | PASS | Three real worker boxes visually inspected on captured pixels; 715.19 ms representative processing sample. |
| Simulated USB | PASS | A/B selection, denied permission, unavailable source, capture, genuine inference, disconnect/reconnect; zero streams/tracks after stop. |
| Local MP4 | PASS | Actual file chooser, three person detections, pause/resume at 0.5×; source-specific persisted session. |
| Simulation | PASS | Nine steps completed: two entries, two exits, one re-entry; labeled fixtures. |
| Incident review | PASS | Severity/zone/type filters, empty filter, export of both IDs, modal focus trap/Escape, acknowledgment 0→1→0 in QA copy. |
| Analytics | PASS | Two high-severity RestrictedZone incidents; stored totals and acknowledgments matched SQLite/API. |
| Zones | PASS | Disposable QA zone saved; draft cancel retained the saved name; explicit deletion; original zone untouched. |
| Integration | PASS | Real API/AI health checks, copied HTTP/WebSocket addresses, actual GitHub schema link, replay-mode ingestion boundaries. |
| Unavailable AI service | PASS | Dedicated temporary frontend pointed at a closed AI port; V2 remained healthy, unavailable operations disabled. |
| Keyboard and accessibility | PASS | Source-card Home/End, polygon controls, dialog trapping, page-heading focus, expanded navigation state, hidden mobile navigation, preview labeling and reduced motion. |
| Physical USB / INT8 / Jetson / FirmGen hardware | NOT TESTED | No corresponding hardware or optimization execution claim. |
| Formal independent detection accuracy | PENDING HUMAN REVIEW | No precision, recall, F1, mAP or threshold-accuracy claim. |

## Scope and limits

API/WebSocket and temporary-database restart contracts passed. The working host services were not restarted; unavailable-service UI testing used a separate temporary proxy and left the genuine CPU worker healthy. Two existing test warnings remain: Starlette/AnyIO deprecation and duplicate OpenAPI operation ID for replay-video GET/HEAD. No comprehensive WCAG conformance audit is claimed.

Original incident records, acknowledgment states, zone coordinates and media/model/metadata hashes were compared before and after. Large artifacts and the existing release archive remain external to ordinary Git.

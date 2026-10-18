# Three-page frontend release

Only Overview, Recorded Monitoring and Incident Center are redesigned. Changes use existing React components and dependencies; no backend, PipeGen, model, timing/synchronization or production threshold changes. Shared shell styles apply only while one of these three pages is selected. The independent AI interface and other pages keep their prior styling.

## Reference comparison and visual correction

The supplied screenshots guide the pale sidebar, compact breadcrumb topbar, white bordered cards, navy headings, green connection/person indicators, red zones/severity and restrained blue actions. Overview is video plus pipeline with recent incidents below; Recorded Monitoring is a full-width video card; Incident Center is a header/replay shortcut, optional analysis and filterable table.

Actual data intentionally differs from the references: source duration 10.16 s, original 2026 incident timestamps, IDs 0/1/2 and actual confidences, genuine person boxes and original frame-relative rectangle. The source camera moves. No screenshot dates, duration or decorative detections were copied. The full 16:9 source remains visible rather than adopting reference image crops; desktop views may scroll vertically to controls/recent incidents.

The first screenshot pass found an inherited dark filter strip. It was corrected to white, Overview chrome was tightened, text contrast improved, and keyboard dialog focus/recovery verified. Captures are actual browser viewport screenshots. Additional controls/table screenshots show content below the fold; they are not composited mockups.

## Actual validation

231 backend tests and35 frontend tests passed, with TypeScript and production build. Existing actual-model HTTP/WebSocket cases exercised virtual, uploaded and simulated USB sources. No test skip. Browser: playback, pause, seek, 4× speed, end, replay, reload, refresh,all three filters,downloaded JSON with two exact IDs,details,keyboard/mobile dialog,SQLite acknowledgment in an isolated database copy,optional analysis expand/collapse,and independent simulation/real CPU frame. Original live two incidents and acknowledgment states remained untouched. The copy's test acknowledgment was restored.

All three pages were visually inspected at1600 × 900, 1920 × 1080, 1366 × 768, and 390 × 844. No page horizontal overflow; mobile table uses internal scrolling. Video/SVG origin mapping agrees,person-box drift below 0.001 px on inspected frames, and PTS difference 0 ms. Frame 38: three detections,one inside. Frame 106: three detections,zero inside. Frame 245: no stale person boxes. The polygon stays806,799 /1190,799 /1190,929 /806,929at1920 × 1080.

See [acceptance JSON](../evidence/ui-light-redesign/acceptance.json),[layout/alignment measurements](../evidence/ui-light-redesign/browser-layout-and-alignment.json),[preservation](../evidence/ui-light-redesign/preservation.json)and[actual test output](../evidence/ui-light-redesign/tests.txt).

## Screenshots

| Page | Desktop1600 × 900 | Mobile390 × 844 |
| --- | --- | --- |
| Overview | [Video and pipeline](../evidence/ui-light-redesign/design-overview-desktop.png),[recent incidents below](../evidence/ui-light-redesign/design-overview-incidents.png) | [Mobile](../evidence/ui-light-redesign/design-overview-mobile.png) |
| Recorded Monitoring | [Header and video](../evidence/ui-light-redesign/design-monitoring-desktop.png),[controls](../evidence/ui-light-redesign/design-monitoring-controls.png) | [Mobile](../evidence/ui-light-redesign/design-monitoring-mobile.png) |
| Incident Center | [Desktop](../evidence/ui-light-redesign/design-incidents-desktop.png) | [Filters/table](../evidence/ui-light-redesign/design-incidents-mobile.png),[actions](../evidence/ui-light-redesign/design-incidents-mobile-actions.png),[details](../evidence/ui-light-redesign/design-incidents-mobile-details.png) |

Wide and laptop captures are saved alongside these images,as are real entry/empty-frame alignment screenshots.

## Launch

Use the existing [setup](setup.md)and[warehouse guide](factory-release.md). Primary frontend:

```bash
cd frontend
npm run dev -- --port 5173
```

 Set the existing `SENTINEL_API_TARGET`/`SENTINEL_AI_TARGET`to match chosen backend ports. Current demo uses V2 backend 8003 and independent service 8005; defaults remain 8000 and 8004. A separate QA frontend 5181 used a SQLite snapshot on 8006 to test acknowledgment without changing live V2. No new dependencies were installed.

Independent accuracy remains PENDING HUMAN REVIEW. Physical USB hardware, INT8 execution, Jetson and FirmGen closed-loop hardware remain NOT TESTED. This UI release does not add measured accuracy or hardware evidence.

## Post-merge validation

[Post-merge acceptance](../evidence/ui-light-redesign/postmerge-acceptance.json) records the executed 231 backend / 35 frontend tests, TypeScript, production build and API smoke checks. [The full 254-frame HTTP/WebSocket/SQLite check](../evidence/ui-light-redesign/postmerge-api-websocket-sqlite.json) passed in a new verification database. The live original two incidents and acknowledgments remained exactly unchanged. The main URL was visually inspected after merge; [this screenshot](../evidence/ui-light-redesign/released-overview.png) shows the released frontend.

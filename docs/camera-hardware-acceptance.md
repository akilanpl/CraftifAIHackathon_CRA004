# USB camera hardware acceptance — NOT TESTED

The user owns an unavailable/unusable USB camera and has no real factory environment. This procedure is for a later working camera. Browser mocks and prerecorded-video inference do not constitute physical camera testing or deployment validation.

## Preconditions

- Storage guard passes with at least 1 GiB root and 20 GiB external reserve.
- Independent runtime/model has genuinely processed real video frames; inference unavailable is an explicit failure state.
- Warehouse V2 remains available, unchanged, with its original incident IDs and acknowledgments.
- Run on localhost or an HTTPS origin for browser camera permission. Use a controlled ordinary indoor scene; do not test near an actual hazard.
- Choose a fixed view with visible floor and identifiable people. The polygon is a configured image region, not a certified physical safety boundary.

## Automated browser states before hardware

Mock permission denial, no video-input device, device busy, capture failure, ended/disconnected track and permission revocation. Confirm actionable errors, no invented live frame/detection, no stale overlay, no frame-queue growth and successful cleanup. Permission must be requested by a user action. Starting USB mode must not automatically activate on page load. Stopping must call the browser capture-track stop operation and remove video references.

## Manual hardware procedure

1. Connect a working USB camera. Open AI Camera Monitor, choose USB Camera, select the device and grant permission intentionally.
2. Confirm the actual camera image and correct device/source label. Show **independent inference** and actual measured status, not V2 replay metadata. Verify the physical-camera NOT TESTED label changes only after recorded acceptance, not merely after permission succeeds.
3. Define/save a normalized zone on the visible floor. Inspect displayed overlay and actual source dimensions at wide and narrow viewport sizes. Verify source-image/overlay placement, including black bars or crop behavior.
4. Start monitoring. Stand outside, approach, enter, hold, exit, re-enter and exit again. Review image, source timestamps and genuine model detections. Check one entry per observed tracked entry, no hold spam and explicit exit/reentry semantics.
5. Include two people, brief occlusion and a temporarily missed detection. Verify honest tracker status and timeout semantics. Do not claim identity across occlusion without evidence.
6. Inspect an incident and acknowledge it. Refresh/restart as supported and verify that source/session IDs, incident IDs and acknowledgment states remain correct. Confirm no Warehouse V2 incident was added, removed or changed.
7. Exercise a slow inference response and disconnect/reconnect the service. Observe bounded in-flight work and removal of stale boxes. Check source/frame correlation; old responses must not overlay a newer unrelated frame.
8. Stop monitoring. Verify the camera indicator goes off, browser video tracks are stopped and resources are released. Unplug during capture, deny a later request, switch device and close the module; each should clean up and report the actual state.
9. Save actual logs, screenshots, model/provider details, measured frame latency/FPS and browser/device versions. Mark PHYSICAL CAMERA HARDWARE TEST PASSED only after this procedure succeeds, with limitations recorded.

Do not describe this indoor acceptance as factory validation. Do not test a real unsafe event or rely on this prototype for protective control.

## Manual real-frame annotation template

Create annotations by independently reviewing the original frame, preferably without viewing predictions first. Use exact video hash, frame index and PTS; draw pixel `[x1,y1,x2,y2]` boxes around visible persons and state occlusion/truncation policy. Annotator must explicitly mark review completion; model predictions may assist a separate pass but cannot serve as independent truth.

```json
{
  "schema_version": 1,
  "source_sha256": "REPLACE_WITH_ACTUAL_VIDEO_SHA256",
  "frame_index": 0,
  "pts_ns": 0,
  "frame_width": 1920,
  "frame_height": 1080,
  "annotation_status": "UNREVIEWED_TEMPLATE",
  "annotator": "REQUIRED_AFTER_MANUAL_REVIEW",
  "reviewed_without_predictions": false,
  "persons": [],
  "review_notes": "Empty persons is not a verified negative until a human reviews this exact frame."
}
```

Keep whole videos/scenes separated between evaluation splits. Store model predictions in a different file linked by the same source/frame identity. Report reviewed frame/person counts, IoU matching threshold, confidence threshold, precision/recall/F1 and any applicable mAP only after actual independent evaluation. Record ambiguous persons, annotation limits and per-scene errors. A few frames are a small diagnostic set, not a reliable general factory-accuracy benchmark.

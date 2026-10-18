# Real-world demo footage preparation

Status: **PENDING — no real test footage supplied or processed.** Do not add generated people, downloaded datasets, or synthetic screenshots as real inference evidence.

## Record a small, useful clip

Use a phone or USB camera in a safe room. Represent the restricted area with tape on an ordinary floor; do not enter an actual hazardous workplace. Keep the camera fixed, landscape, with the whole person and feet visible, steady lighting and no digital zoom. Ask participants before recording. Choose standard **H.264/AVC video in an MP4 container**, 1280×720, 25 or 30 fps if your device offers those choices. This is a conservative DeepStream candidate, not a claim that every PipeGen v0.5.1 decoder configuration supports it.

Record 30–40 seconds:

| Time | Action | Expected safety event after integration |
| --- | --- | --- |
| 0–5 s | Person stands outside the taped region | No entry |
| 5–10 s | Walk across the boundary and hold inside | One entry; holding adds none |
| 10–15 s | Walk outside and remain visible | Occupancy clears |
| 15–20 s | Re-enter | One new entry |
| 20–30 s | A second person enters while the first remains inside | One entry per stable tracker identity |
| 30–35 s | Both leave, remain visible outside | Occupancy returns to zero |

Keep file size modest: around 4 Mb/s for 35 seconds is approximately 18 MB. Disable HDR/HEVC if your phone offers a compatibility setting. No transcoder is installed here; do not install tools or transcode while the PipeGen runtime is downloading merely to prepare this clip.

## Where to provide it

Keep original footage on your already-mounted external storage. Inspection found `/mnt/seagate4/PipeGenHackathon`; do not use the older unmounted `/media/vijayababu/SeaGate4/...` path. Confirm the external path with the setup operator before writing. This project has `demo-video/input/` and `demo-video/capture/` placeholders only; large video extensions are Git-ignored. Do not copy large recordings onto the root partition.

Give the PipeGen operator the **absolute host path**, codec/container, width/height, fps, duration, approximate entry/exit times and permission to use the footage. The operator must make that path available inside the generated runtime using its existing input mechanism. Host and container paths may differ; this project does not modify container mounts. Start with a local file, then try USB/RTSP only when the selected pipeline supports them.

Retain the original and calculate its checksum with `sha256sum /actual/external/path/entry-test.mp4`. Fill `clip-manifest.example.json` with actual values and remove `.example` from your working copy outside Git if it contains private locations. Optional `ffprobe` inspection is useful **if already installed**; it was absent during this preparation, and none was downloaded.

## Verified input support and limits

- CraftifAI's current product page discusses USB/GStreamer/RTSP camera integration but does not provide a version-specific file/codec compatibility table: [PipeGen product page](https://craftifai.com/products/pipegen).
- NVIDIA documents local MP4/H.264/H.265, RTSP and USB source patterns in its official repository: [DeepStream source assembly rules](https://github.com/NVIDIA/DeepStream/blob/main/skills/deepstream-generate-pipeline/references/assembly-rules.md).
- NVIDIA's reference application lists URI/file, RTSP and V4L2 camera configuration: [DeepStream reference application](https://docs.nvidia.com/metropolis/deepstream/9.0/text/DS_ref_app_deepstream.html). These are DeepStream capabilities, not proof of the installed PipeGen version's exposed controls.
- `/opt/PipeGen/PipeGenApp` and bundled UI assets were found. No packaged README/config compatibility table was found in the inspected directories. The app was not launched or changed by this task. Actual PipeGen v0.5.1 format acceptance remains **PENDING** until its source selector/export/runtime is inspected by the PipeGen operator.

Sources checked October 18, 2026. No numeric DeepStream source-type code is prescribed here because generated runtime versions and source plugins differ.

## Capture the real end-to-end demonstration

After genuine integration, screen-record the real PipeGen Run output and the dashboard in **LIVE INPUT MODE**. Show outside → entry → hold → exit → re-entry, then inspect the stored incident and acknowledge it. Keep timestamp/camera/track IDs visible and retain the raw metadata for the same sequence. Use the actual compiled TensorRT FP16 report in the presentation; API response time and synthetic tests are not inference performance. Put links and checksums in the evidence ledger only after verification.

Narration: `docs/demo-script.md`. Exact metadata handoff: `docs/pipegen-handoff.md`.

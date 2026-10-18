#!/usr/bin/env python3
"""Forward JSONL to an explicit ingestion endpoint; stdlib only, no schema guesses.

For canonical files use --endpoint detections. For native PipeGen files use
--endpoint pipegen, which intentionally rejects data until its parser is configured.
Stops on malformed input or rejected ingestion instead of silently dropping events.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--endpoint', required=True, choices=['detections', 'pipegen'])
    parser.add_argument('--follow', action='store_true', help='Wait for appended complete lines')
    parser.add_argument('--from-end', action='store_true', help='Skip existing lines')
    args = parser.parse_args()
    url = args.base_url.rstrip('/') + '/api/ingest/' + args.endpoint
    with args.file.open(encoding='utf-8') as stream:
        if args.from_end:
            stream.seek(0, 2)
        line_number = 0
        while True:
            position = stream.tell()
            line = stream.readline()
            if not line or (args.follow and not line.endswith('\n')):
                stream.seek(position)
                if args.follow:
                    time.sleep(0.25)
                    continue
                break
            line_number += 1
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                request = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                                 headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(request, timeout=10) as response:
                    print(f'line {line_number}: HTTP {response.status}', flush=True)
            except (ValueError, urllib.error.URLError) as exc:
                detail = exc.read().decode(errors='replace') if isinstance(exc, urllib.error.HTTPError) else str(exc)
                raise SystemExit(f'Ingestion stopped at line {line_number}: {detail}') from exc


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)

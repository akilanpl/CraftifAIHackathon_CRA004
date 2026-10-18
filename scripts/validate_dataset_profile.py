#!/usr/bin/env python3
"""Validate a local explicitly paired dataset; performs no inference or ingestion."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.profiles import DatasetProfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',help='Path to the reviewed dataset profile manifest')
    parser.add_argument('--scene',choices=['factory','historical_street'],default='factory')
    args=parser.parse_args()
    profile=DatasetProfile(args.manifest,args.scene)
    print(json.dumps(profile.public(),indent=2))
    return 0 if profile.state=='READY' else 2


if __name__=='__main__':
    raise SystemExit(main())

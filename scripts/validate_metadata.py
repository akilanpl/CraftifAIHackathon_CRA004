"""Validate locally without ingesting, storing, or claiming genuine PipeGen evidence."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.models import Frame
from backend.adapters.field_mapping import FieldMappingParser

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('record',type=Path,help='One JSON frame record')
    parser.add_argument('--mapping',type=Path,help='Reviewed explicit field-mapping JSON; omit for canonical input')
    args=parser.parse_args()
    try:
        raw=json.loads(args.record.read_text())
        frame=FieldMappingParser(json.loads(args.mapping.read_text()))(raw) if args.mapping else Frame.model_validate(raw)
    except (ValueError,OSError,TypeError,KeyError) as exc:
        parser.exit(2,'Metadata rejected: '+str(exc)+'\n')
    print(frame.model_dump_json(indent=2))
    print('VALIDATED LOCALLY ONLY: no API ingestion, database writes, or PipeGen provenance claimed.',file=sys.stderr)
if __name__=='__main__':
    main()

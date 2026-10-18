"""Operator-configured dataset profiles. No asset discovery or street fallback."""
import hashlib
import json
import os
from pathlib import Path
from typing import Literal
from pydantic import Field, ValidationError, model_validator
from .models import StrictModel, ZoneInput, Zone
from .replay import load_export


class ProfileManifest(StrictModel):
    version: Literal[1]
    id: str = Field(pattern=r'^[a-z][a-z0-9-]{0,63}$')
    name: str = Field(min_length=1,max_length=120)
    description: str = Field(default='',max_length=1000)
    scene_type: Literal['factory','historical_street']
    source_kind: Literal['recorded_pipegen']
    video_path: str = Field(min_length=1)
    metadata_path: str = Field(min_length=1)
    video_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    metadata_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    frame_width: int = Field(strict=True,gt=0,le=32768)
    frame_height: int = Field(strict=True,gt=0,le=32768)
    source_id: int = Field(strict=True,ge=0)
    camera_id: str = Field(min_length=1,max_length=80)
    pts_offset_ns: int = Field(strict=True)
    pts_mapping_verified: Literal[True]
    pts_verification_note: str = Field(min_length=1,max_length=1000)
    model_name: str = Field(min_length=1,max_length=120)
    precision: str = Field(min_length=1,max_length=50)
    zones: list[ZoneInput] = Field(default_factory=list,max_length=64)
    tolerance_ns: int = Field(default=8350000,strict=True,ge=0,le=1000000000)

    @model_validator(mode="before")
    @classmethod
    def explicit_verification(cls,value):
        if isinstance(value,dict) and value.get("pts_mapping_verified") is not True:
            raise ValueError("pts_mapping_verified must be the JSON boolean true")
        return value

    @model_validator(mode="after")
    def explicit_factory_zones(self):
        if any(not getattr(self,key).strip() for key in ("name","camera_id","model_name","precision","pts_verification_note")):
            raise ValueError("Profile identity, model and PTS verification fields cannot be blank")
        if self.scene_type=="factory" and not self.zones:
            raise ValueError("Factory profile requires explicitly configured zones")
        if any(z.camera_id!=self.camera_id for z in self.zones):
            raise ValueError("Profile zone camera must match manifest camera")
        return self


def file_sha256(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda:source.read(1024*1024),b''):
            digest.update(chunk)
    return digest.hexdigest()


def identity(path):
    stat=Path(path).stat()
    return stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns


class ProfileError(ValueError):
    def __init__(self,code,message):
        super().__init__(message)
        self.code=code


def validate_mp4_container(path):
    """Check bounded top-level ISO-BMFF box structure, not codec decodability.

    Reads only box headers and ftyp brands. mdat/video samples stay on disk.
    Browser decoding and frame alignment remain separately verified evidence.
    """
    size=Path(path).stat().st_size
    found=set()
    video_track=False
    with Path(path).open('rb') as handle:
        # Match the streaming endpoint's supported initial MP4 signature.
        if b'ftyp' not in handle.read(64):
            raise ProfileError('VIDEO_CONTAINER_INVALID','Configured video does not expose the supported MP4 signature')

        def children(start,end):
            position=start
            inspected=0
            while position<end:
                inspected+=1
                if inspected>100000 or end-position<8:
                    raise ProfileError('VIDEO_CONTAINER_INVALID','MP4 movie index contains truncated child boxes')
                handle.seek(position)
                header=handle.read(8)
                length=int.from_bytes(header[:4],'big');header_size=8
                if length==1:
                    extended=handle.read(8)
                    if len(extended)!=8:
                        raise ProfileError('VIDEO_CONTAINER_INVALID','MP4 movie index extended header is truncated')
                    length=int.from_bytes(extended,'big');header_size=16
                elif length==0:
                    length=end-position
                if length<header_size or position+length>end:
                    raise ProfileError('VIDEO_CONTAINER_INVALID','MP4 movie index child length exceeds its parent')
                yield header[4:],position+header_size,position+length
                position+=length

        offset=0
        count=0
        while offset<size:
            count+=1
            if count>100000 or size-offset<8:
                raise ProfileError('VIDEO_CONTAINER_INVALID','MP4 contains truncated or excessive top-level boxes')
            handle.seek(offset)
            header=handle.read(8)
            box_size=int.from_bytes(header[:4],'big')
            kind=header[4:]
            header_size=8
            if box_size==1:
                extended=handle.read(8)
                if len(extended)!=8:
                    raise ProfileError('VIDEO_CONTAINER_INVALID','MP4 extended box header is truncated')
                box_size=int.from_bytes(extended,'big');header_size=16
            elif box_size==0:
                box_size=size-offset
            if box_size<header_size or offset+box_size>size:
                raise ProfileError('VIDEO_CONTAINER_INVALID','MP4 box length exceeds the configured file')
            if kind==b'ftyp':
                if box_size-header_size<8:
                    raise ProfileError('VIDEO_CONTAINER_INVALID','MP4 ftyp box lacks its brand and version')
                brands=handle.read(min(box_size-header_size,256))
                if not any(brand in brands for brand in (b'isom',b'iso2',b'iso3',b'iso4',b'iso5',b'iso6',b'avc1',b'mp41',b'mp42',b'M4V ')):
                    raise ProfileError('VIDEO_CONTAINER_UNSUPPORTED','Configured container does not identify a supported MP4 brand')
            if kind in (b'moov',b'mdat') and box_size==header_size:
                raise ProfileError('VIDEO_CONTAINER_INVALID','MP4 movie index or media data is empty')
            if kind==b'moov':
                for child,start,end in children(offset+header_size,offset+box_size):
                    if child!=b'trak':continue
                    for track_part,track_start,track_end in children(start,end):
                        if track_part!=b'mdia':continue
                        for media_part,media_start,media_end in children(track_start,track_end):
                            if media_part==b'hdlr':
                                if media_end-media_start<12:
                                    raise ProfileError('VIDEO_CONTAINER_INVALID','MP4 media handler is truncated')
                                handle.seek(media_start+8)
                                video_track=video_track or handle.read(4)==b'vide'
            found.add(kind)
            offset+=box_size
    if not {b'ftyp',b'moov',b'mdat'}.issubset(found):
        raise ProfileError('VIDEO_CONTAINER_INCOMPLETE','MP4 requires ftyp, moov movie index, and mdat media data boxes')
    if not video_track:
        raise ProfileError('VIDEO_TRACK_MISSING','Configured MP4 does not declare a video track in its movie index')


class DatasetProfile:
    def __init__(self,manifest_path=None,requested=None):
        self.manifest_path=manifest_path or os.getenv('SENTINEL_PROFILE_PATH')
        self.requested=requested or os.getenv('SENTINEL_DATASET_PROFILE')
        self.explicit=bool(self.manifest_path or self.requested)
        self.manifest=None
        self.video_path=self.metadata_path=None
        self.identities={}
        self.errors=[]
        self.error_code=None
        self.state='PENDING' if self.explicit else 'LEGACY'
        self.id='factory-pending' if self.requested=='factory' else 'historical-street'
        self.scene_type='factory' if self.requested=='factory' else 'historical_street'
        if self.requested not in (None,'factory','historical_street'):
            self.state='INVALID';self.error_code='PROFILE_SELECTION_INVALID';self.errors=['Unknown explicitly requested dataset profile'];return
        if not self.manifest_path:
            if self.explicit:
                self.error_code='MANIFEST_UNCONFIGURED'
                self.errors=['SENTINEL_PROFILE_PATH must select a reviewed local manifest']
            return
        try:
            manifest_path=Path(self.manifest_path).resolve()
            if not manifest_path.exists():
                self.state='PENDING';self.error_code='MANIFEST_PENDING';self.errors=['The explicitly configured manifest has not arrived'];return
            if not manifest_path.is_file():
                raise ProfileError('MANIFEST_NOT_FILE','Configured profile manifest must be a regular JSON file')
            with manifest_path.open(encoding='utf-8') as handle:
                raw=json.load(handle,object_pairs_hook=self._unique_keys)
            manifest=ProfileManifest.model_validate(raw)
            if self.requested and manifest.scene_type!=self.requested:
                raise ProfileError('SCENE_MISMATCH','Manifest scene does not match the explicitly requested dataset')
            self.manifest=manifest
            self.id,self.scene_type=manifest.id,manifest.scene_type
            self.video_path=self._path(manifest_path,manifest.video_path)
            self.metadata_path=self._path(manifest_path,manifest.metadata_path)
            for label,path in (('video',self.video_path),('metadata',self.metadata_path)):
                if not path.exists():
                    self.state='PENDING';self.error_code='ASSET_PENDING';self.errors=[f'Configured {label} asset has not arrived'];return
                if not path.is_file():
                    raise ProfileError('ASSET_NOT_FILE',f'Configured {label} asset must be a regular file')
            before={str(path):identity(path) for path in (self.video_path,self.metadata_path)}
            if self.video_path==self.metadata_path or self.video_path.suffix.lower()!='.mp4':
                raise ProfileError('ASSET_PAIR_INVALID','Profile requires distinct MP4 video and metadata files')
            if file_sha256(self.video_path)!=manifest.video_sha256 or file_sha256(self.metadata_path)!=manifest.metadata_sha256:
                raise ProfileError('ASSET_HASH_MISMATCH','Video or metadata SHA-256 differs from the reviewed manifest pair')
            validate_mp4_container(self.video_path)
            try:
                frames,_,_=load_export(self.metadata_path)
            except (ValueError,KeyError,TypeError,OverflowError):
                raise ProfileError('METADATA_INVALID','Configured metadata failed canonical replay schema validation') from None
            if any((f['width'],f['height'],f['source_id'])!=(manifest.frame_width,manifest.frame_height,manifest.source_id) for f in frames):
                raise ProfileError('METADATA_PROFILE_MISMATCH','Metadata dimensions or source differ from the reviewed manifest')
            after={str(path):identity(path) for path in (self.video_path,self.metadata_path)}
            if before!=after:
                raise ProfileError('ASSET_CHANGED','Profile assets changed during verification; retry only after the producer finishes writing')
            self.identities=after
            self.state='READY'
        except Exception as exc:
            self.state='INVALID'
            if isinstance(exc,ProfileError):
                self.error_code=exc.code;self.errors=[str(exc)]
            elif isinstance(exc,ValidationError):
                self.error_code='MANIFEST_SCHEMA_INVALID'
                fields=sorted({'.'.join(str(part) for part in error['loc']) or 'manifest' for error in exc.errors()})
                self.errors=['Manifest schema validation failed for: '+', '.join(fields)]
            elif isinstance(exc,json.JSONDecodeError):
                self.error_code='MANIFEST_JSON_INVALID';self.errors=['Manifest is not valid JSON']
            elif isinstance(exc,OSError):
                self.error_code='ASSET_IO_ERROR';self.errors=['Configured manifest or asset cannot be read; check local permissions']
            else:
                self.error_code='PROFILE_CONFIGURATION_INVALID';self.errors=['Profile configuration is invalid; review manifest paths and duplicate keys']

    @staticmethod
    def _unique_keys(pairs):
        result={}
        for key,value in pairs:
            if key in result:
                raise ProfileError('MANIFEST_DUPLICATE_KEY','Manifest contains duplicate JSON keys; use exactly one value per setting')
            result[key]=value
        return result

    @staticmethod
    def _path(manifest_path,value):
        path=Path(value)
        if '\x00' in value or '://' in value:
            raise ProfileError('ASSET_PATH_INVALID','Asset paths must reference explicitly configured local files')
        return (path if path.is_absolute() else manifest_path.parent/path).resolve()

    def integrity(self):
        if self.state!='READY':return False
        try:
            valid=all(identity(path)==expected for path,expected in self.identities.items())
        except OSError:
            valid=False
        if not valid:
            self.state='INVALID'
            self.error_code='ASSET_CHANGED'
            self.errors=['A verified profile asset changed; restart and reverify before playback']
        return valid

    def public(self):
        if self.state=='READY':self.integrity()
        m=self.manifest
        return dict(id=self.id,name=m.name if m else ('Factory dataset pending' if self.scene_type=='factory' else 'Historical street replay'),description=m.description if m else ('Awaiting genuine factory video and matching PipeGen metadata' if self.scene_type=='factory' else 'Historical street dataset; no factory claim'),scene_type=self.scene_type,source_kind='recorded_pipegen',state=self.state,verified=self.state=='READY',model_name=m.model_name if m and self.state=='READY' else None,precision=m.precision if m and self.state=='READY' else None,metadata_sha256=m.metadata_sha256 if m else None,video_sha256=m.video_sha256 if m else None,errors=self.errors,error_code=self.error_code,media_validation='container_structure' if self.state=='READY' else 'unverified',video_decode_verified=False,requirements=[] if self.state=='READY' else ['Explicit paired video and genuine metadata','Matching SHA-256 hashes','Verified PTS offset, dimensions and source'])

    def bind_database(self,db):
        if not self.explicit:
            with db.lock:
                exists=db.conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='dataset_profile'").fetchone()
                if exists and db.conn.execute('SELECT 1 FROM dataset_profile').fetchone():
                    raise ValueError('A profile-bound database requires its explicit dataset profile; legacy/live sources are refused')
            return
        m=self.manifest
        dataset=hashlib.sha256(json.dumps([m.metadata_sha256,m.video_sha256,m.pts_offset_ns,m.frame_width,m.frame_height,m.source_id,m.camera_id,m.model_name,m.precision],separators=(',',':')).encode()).hexdigest() if m and self.state=='READY' else None
        with db.lock,db.conn:
            db.conn.execute('CREATE TABLE IF NOT EXISTS dataset_profile (singleton INTEGER PRIMARY KEY CHECK(singleton=1), profile_id TEXT NOT NULL, scene_type TEXT NOT NULL, metadata_sha256 TEXT)')
            row=db.conn.execute('SELECT profile_id,scene_type,metadata_sha256 FROM dataset_profile WHERE singleton=1').fetchone()
            populated=db.conn.execute('SELECT COUNT(*) FROM incidents').fetchone()[0] or db.conn.execute('SELECT COUNT(*) FROM zones').fetchone()[0]
            if row is None:
                if populated:raise ValueError('Profile refuses a nonempty unbound database; choose a separate dataset database')
                db.conn.execute('INSERT INTO dataset_profile VALUES (1,?,?,?)',(self.id,self.scene_type,dataset))
            elif row[2] is None and dataset is not None and row[1]==self.scene_type and (row[0]==self.id or row[0]=='factory-pending'):
                if db.conn.execute('SELECT COUNT(*) FROM incidents').fetchone()[0]:
                    raise ValueError('Pending dataset database contains incidents and cannot be relabeled')
                try:
                    existing=[Zone.model_validate(zone) for zone in db.zones()]
                    if any(zone.camera_id!=m.camera_id for zone in existing):
                        raise ValueError('Zone camera mismatch')
                except (ValidationError,ValueError):
                    raise ValueError('Pending zones do not match the verified profile camera; choose a fresh database or explicitly repair zone configuration') from None
                db.conn.execute('UPDATE dataset_profile SET profile_id=?,metadata_sha256=? WHERE singleton=1',(self.id,dataset))
            elif row[:2]!=(self.id,self.scene_type) or (row[2] is not None and dataset is not None and row[2]!=dataset):
                raise ValueError('Database belongs to another dataset profile; choose a separate database')
            elif row[2] is None and dataset is not None:
                if populated:raise ValueError('Pending dataset database must be empty before asset binding')
                db.conn.execute('UPDATE dataset_profile SET metadata_sha256=? WHERE singleton=1',(dataset,))

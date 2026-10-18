"""Operator-configured dataset profiles. No asset discovery or street fallback."""
import hashlib
import json
import os
from pathlib import Path
from typing import Literal, Optional
from pydantic import Field, model_validator
from .models import StrictModel, ZoneInput
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

    @model_validator(mode="after")
    def explicit_factory_zones(self):
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


class DatasetProfile:
    def __init__(self,manifest_path=None,requested=None):
        self.manifest_path=manifest_path or os.getenv('SENTINEL_PROFILE_PATH')
        self.requested=requested or os.getenv('SENTINEL_DATASET_PROFILE')
        self.explicit=bool(self.manifest_path or self.requested)
        self.manifest=None
        self.video_path=self.metadata_path=None
        self.identities={}
        self.errors=[]
        self.state='PENDING' if self.explicit else 'LEGACY'
        self.id='factory-pending' if self.requested=='factory' else 'historical-street'
        self.scene_type='factory' if self.requested=='factory' else 'historical_street'
        if self.requested not in (None,'factory','historical_street'):
            self.state='INVALID';self.errors=['Unknown explicitly requested dataset profile'];return
        if not self.manifest_path:
            return
        try:
            manifest_path=Path(self.manifest_path).resolve()
            if not manifest_path.is_file():
                self.state='PENDING';return
            with manifest_path.open(encoding='utf-8') as handle:
                raw=json.load(handle,object_pairs_hook=self._unique_keys)
            manifest=ProfileManifest.model_validate(raw)
            if self.requested and manifest.scene_type!=self.requested:
                raise ValueError('Manifest scene does not match the requested dataset')
            self.manifest=manifest
            self.id,self.scene_type=manifest.id,manifest.scene_type
            self.video_path=self._path(manifest_path,manifest.video_path)
            self.metadata_path=self._path(manifest_path,manifest.metadata_path)
            if not self.video_path.is_file() or not self.metadata_path.is_file():
                self.state='PENDING';return
            before={str(path):identity(path) for path in (self.video_path,self.metadata_path)}
            if self.video_path==self.metadata_path or self.video_path.suffix.lower()!='.mp4':
                raise ValueError('Profile requires distinct MP4 video and metadata files')
            if file_sha256(self.video_path)!=manifest.video_sha256 or file_sha256(self.metadata_path)!=manifest.metadata_sha256:
                raise ValueError('Profile asset SHA-256 does not match the explicit video/metadata pair')
            frames,_,_=load_export(self.metadata_path)
            if any((f['width'],f['height'],f['source_id'])!=(manifest.frame_width,manifest.frame_height,manifest.source_id) for f in frames):
                raise ValueError('Metadata dimensions or source do not match the profile manifest')
            after={str(path):identity(path) for path in (self.video_path,self.metadata_path)}
            if before!=after:
                raise ValueError('Profile assets changed during verification')
            self.identities=after
            self.state='READY'
        except Exception as exc:
            self.state='INVALID'
            # Paths and raw validation input may include private filesystem names.
            self.errors=['Profile verification failed ('+type(exc).__name__+'); review the local manifest and asset pairing']

    @staticmethod
    def _unique_keys(pairs):
        result={}
        for key,value in pairs:
            if key in result:
                raise ValueError('Duplicate manifest key')
            result[key]=value
        return result

    @staticmethod
    def _path(manifest_path,value):
        path=Path(value)
        if '\x00' in value:
            raise ValueError('Invalid asset path')
        return (path if path.is_absolute() else manifest_path.parent/path).resolve()

    def integrity(self):
        if self.state!='READY':return False
        try:
            valid=all(identity(path)==expected for path,expected in self.identities.items())
        except OSError:
            valid=False
        if not valid:
            self.state='INVALID'
            self.errors=['A verified profile asset changed; restart and reverify before playback']
        return valid

    def public(self):
        if self.state=='READY':self.integrity()
        m=self.manifest
        return dict(id=self.id,name=m.name if m else ('Factory dataset pending' if self.scene_type=='factory' else 'Historical street replay'),description=m.description if m else ('Awaiting genuine factory video and matching PipeGen metadata' if self.scene_type=='factory' else 'Historical street dataset; no factory claim'),scene_type=self.scene_type,source_kind='recorded_pipegen',state=self.state,verified=self.state=='READY',model_name=m.model_name if m and self.state=='READY' else None,precision=m.precision if m and self.state=='READY' else None,metadata_sha256=m.metadata_sha256 if m else None,video_sha256=m.video_sha256 if m else None,errors=self.errors,requirements=[] if self.state=='READY' else ['Explicit paired video and genuine metadata','Matching SHA-256 hashes','Verified PTS offset, dimensions and source'])

    def bind_database(self,db):
        if not self.explicit:
            with db.lock:
                exists=db.conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='dataset_profile'").fetchone()
                if exists and db.conn.execute('SELECT 1 FROM dataset_profile').fetchone():
                    raise ValueError('A profile-bound database requires its explicit dataset profile; legacy/live sources are refused')
            return
        m=self.manifest
        dataset=hashlib.sha256(json.dumps([m.metadata_sha256,m.video_sha256,m.pts_offset_ns,m.frame_width,m.frame_height,m.source_id],separators=(',',':')).encode()).hexdigest() if m and self.state=='READY' else None
        with db.lock,db.conn:
            db.conn.execute('CREATE TABLE IF NOT EXISTS dataset_profile (singleton INTEGER PRIMARY KEY CHECK(singleton=1), profile_id TEXT NOT NULL, scene_type TEXT NOT NULL, metadata_sha256 TEXT)')
            row=db.conn.execute('SELECT profile_id,scene_type,metadata_sha256 FROM dataset_profile WHERE singleton=1').fetchone()
            populated=db.conn.execute('SELECT COUNT(*) FROM incidents').fetchone()[0] or db.conn.execute('SELECT COUNT(*) FROM zones').fetchone()[0]
            if row is None:
                if populated:raise ValueError('Profile refuses a nonempty unbound database; choose a separate dataset database')
                db.conn.execute('INSERT INTO dataset_profile VALUES (1,?,?,?)',(self.id,self.scene_type,dataset))
            elif row[:2]!=(self.id,self.scene_type) or (row[2] is not None and dataset is not None and row[2]!=dataset):
                raise ValueError('Database belongs to another dataset profile; choose a separate database')
            elif row[2] is None and dataset is not None:
                if populated:raise ValueError('Pending dataset database must be empty before asset binding')
                db.conn.execute('UPDATE dataset_profile SET metadata_sha256=? WHERE singleton=1',(dataset,))

"""No native PipeGen schema is assumed. Configure only after inspecting real output.

SENTINEL_PIPEGEN_PARSER=your_module:parse
parse(raw: dict) -> backend.models.Frame | dict using the canonical schema.
Set analytics_mode='native' when mapping genuine native zone analytics.
"""
import importlib
from ..models import Frame


class PipeGenAdapter:
    def __init__(self,parser_path=None):
        self.parser_path = parser_path
        self.parser = None
        if parser_path:
            module, name = parser_path.split(':',1)
            self.parser = getattr(importlib.import_module(module),name)

    def parse(self,raw):
        if self.parser is None:
            raise NotImplementedError('Genuine PipeGen schema adapter is not configured. Supply real metadata and set SENTINEL_PIPEGEN_PARSER=module:callable.')
        value = self.parser(raw)
        return value if isinstance(value,Frame) else Frame.model_validate(value)

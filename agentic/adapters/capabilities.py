"""
Source capability declaration.

A :class:`SourceCapabilityDescriptor` is an adapter's static contract: which
source types and modalities it services and which operations it permits. It is
domain-agnostic — no adapter declares EDGAR-specific vocabulary here.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from agentic.domain.common import DomainModel
from agentic.domain.enums import Modality


class SourceType(str, Enum):
    """Kind of source an adapter can read from."""

    csv = "csv"
    parquet = "parquet"
    sql_query_result = "sql_query_result"
    api_records = "api_records"
    document_collection = "document_collection"
    time_series = "time_series"
    edgar = "edgar"
    in_memory = "in_memory"


class PermittedOperation(str, Enum):
    """Operations an adapter permits on datasets it produces."""

    materialize = "materialize"
    profile_schema = "profile_schema"
    profile_quality = "profile_quality"
    fingerprint = "fingerprint"
    sample = "sample"
    full_scan = "full_scan"


class SourceCapabilityDescriptor(DomainModel):
    """Static declaration of what an adapter supports."""

    adapter_id: str = Field(..., min_length=1)
    adapter_version: str = Field(default="1")
    supported_source_types: list[SourceType]
    supported_modalities: list[Modality]
    permitted_operations: list[PermittedOperation]
    supports_temporal: bool = Field(default=False)
    supports_entity_ids: bool = Field(default=False)
    supports_streaming: bool = Field(default=False)
    notes: str | None = Field(default=None, max_length=512)

    def supports_source_type(self, source_type: SourceType) -> bool:
        return source_type in self.supported_source_types

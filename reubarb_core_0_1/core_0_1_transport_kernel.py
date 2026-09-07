"""Bounded Core 0.1 UTF-8 transport and diagnostic kernel.

This module is host infrastructure only. It does not tokenize, parse, evaluate,
execute, normalize, repair, persist, or interpret Reubarb Pi source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Final, Iterable


INVALID_UTF8: Final[str] = "GART.CORE_0_1.TRANSPORT.INVALID_UTF8"
UTF8_BOM_FORBIDDEN: Final[str] = (
    "GART.CORE_0_1.TRANSPORT.UTF8_BOM_FORBIDDEN"
)

SCHEMA_ID: Final[str] = "gart-transport-observation-0.1"
PROFILE_ID: Final[str] = "core-0.1"
OBSERVATION_KIND: Final[str] = "source-transport"
TRANSPORT_DECODED: Final[str] = "decoded"
TRANSPORT_FAILED: Final[str] = "failed"

_UTF8_BOM: Final[bytes] = b"\xef\xbb\xbf"


@dataclass(frozen=True, slots=True)
class ByteSpan:
    """A zero-based, end-exclusive location in the supplied byte sequence."""

    unit: str = field(default="BYTE", init=False)
    start_offset: int
    end_offset: int

    def __post_init__(self) -> None:
        if type(self.start_offset) is not int or type(self.end_offset) is not int:
            raise TypeError("ByteSpan offsets must be integers.")
        if self.start_offset < 0:
            raise ValueError("ByteSpan start_offset must be non-negative.")
        if self.end_offset < self.start_offset:
            raise ValueError(
                "ByteSpan end_offset must not be less than start_offset."
            )


@dataclass(frozen=True, slots=True)
class ReasonRecord:
    """One approved machine reason with optional host explanation and location."""

    code: str
    message: str | None = None
    location: ByteSpan | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.code, str):
            raise TypeError("ReasonRecord code must be a string.")
        if not self.code:
            raise ValueError("ReasonRecord code must not be empty.")
        if self.message is not None and not isinstance(self.message, str):
            raise TypeError("ReasonRecord message must be a string or None.")
        if self.location is not None and not isinstance(self.location, ByteSpan):
            raise TypeError("ReasonRecord location must be a ByteSpan or None.")


@dataclass(frozen=True, slots=True)
class TransportResult:
    """Host result for one bounded in-memory source-transport inspection."""

    source_id: str
    decoded_text: str | None
    reasons: tuple[ReasonRecord, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str):
            raise TypeError("TransportResult source_id must be a string.")
        if self.decoded_text is not None and not isinstance(self.decoded_text, str):
            raise TypeError("TransportResult decoded_text must be a string or None.")
        if not isinstance(self.reasons, tuple):
            raise TypeError("TransportResult reasons must be a tuple.")
        if any(not isinstance(reason, ReasonRecord) for reason in self.reasons):
            raise TypeError("TransportResult reasons must contain ReasonRecord values.")

        if self.decoded_text is None:
            if not self.reasons:
                raise ValueError(
                    "A failed TransportResult must contain at least one reason."
                )
        elif self.reasons:
            raise ValueError(
                "A successful TransportResult must not contain transport reasons."
            )

    @property
    def succeeded(self) -> bool:
        """Return True only when exact decoded text is available."""

        return self.decoded_text is not None


def _default_message(code: str) -> str | None:
    if code == INVALID_UTF8:
        return "The supplied bytes are not valid UTF-8."
    if code == UTF8_BOM_FORBIDDEN:
        return "Core 0.1 source transport does not permit a leading UTF-8 BOM."
    return None


def _reason_identity(reason: ReasonRecord) -> tuple[str, tuple[str, int, int] | None]:
    location = reason.location
    if location is None:
        location_identity = None
    else:
        location_identity = (
            location.unit,
            location.start_offset,
            location.end_offset,
        )
    return reason.code, location_identity


def _reason_sort_key(reason: ReasonRecord) -> tuple[int, int, int, str]:
    location = reason.location
    if location is None:
        return 1, 0, 0, reason.code
    return 0, location.start_offset, location.end_offset, reason.code


def _deduplicate_and_order_reasons(
    reasons: Iterable[ReasonRecord],
) -> tuple[ReasonRecord, ...]:
    """Deduplicate by code plus location, then apply the approved order."""

    first_by_identity: dict[
        tuple[str, tuple[str, int, int] | None],
        ReasonRecord,
    ] = {}

    for reason in reasons:
        if not isinstance(reason, ReasonRecord):
            raise TypeError("Every reason must be a ReasonRecord.")
        identity = _reason_identity(reason)
        if identity not in first_by_identity:
            first_by_identity[identity] = reason

    return tuple(sorted(first_by_identity.values(), key=_reason_sort_key))


def inspect_source_bytes(source_bytes: bytes, source_id: str) -> TransportResult:
    """Inspect one supplied byte sequence under the approved transport contract."""

    if not isinstance(source_bytes, bytes):
        raise TypeError("source_bytes must be a bytes object.")
    if not isinstance(source_id, str):
        raise TypeError("source_id must be a string.")

    reasons: list[ReasonRecord] = []

    if source_bytes.startswith(_UTF8_BOM):
        reasons.append(
            ReasonRecord(
                code=UTF8_BOM_FORBIDDEN,
                message=_default_message(UTF8_BOM_FORBIDDEN),
                location=ByteSpan(start_offset=0, end_offset=3),
            )
        )

    decoded_candidate: str | None
    try:
        decoded_candidate = source_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        decoded_candidate = None
        reasons.append(
            ReasonRecord(
                code=INVALID_UTF8,
                message=_default_message(INVALID_UTF8),
                location=None,
            )
        )

    ordered_reasons = _deduplicate_and_order_reasons(reasons)
    if ordered_reasons:
        return TransportResult(
            source_id=source_id,
            decoded_text=None,
            reasons=ordered_reasons,
        )

    if decoded_candidate is None:
        raise RuntimeError(
            "Internal transport invariant failed: decoding produced no text "
            "without a transport reason."
        )

    return TransportResult(
        source_id=source_id,
        decoded_text=decoded_candidate,
        reasons=(),
    )


def _reason_to_json_object(reason: ReasonRecord) -> dict[str, object]:
    payload: dict[str, object] = {"code": reason.code}

    if reason.location is not None:
        payload["location"] = {
            "unit": reason.location.unit,
            "start_offset": reason.location.start_offset,
            "end_offset": reason.location.end_offset,
        }

    return payload


def serialize_transport_result(result: TransportResult) -> str:
    """Serialize one bounded source-free transport observation as JSON text."""

    if not isinstance(result, TransportResult):
        raise TypeError("result must be a TransportResult.")

    payload: dict[str, object] = {
        "schema": SCHEMA_ID,
        "profile": PROFILE_ID,
        "observation_kind": OBSERVATION_KIND,
        "source_id": result.source_id,
        "transport_result": (
            TRANSPORT_DECODED if result.succeeded else TRANSPORT_FAILED
        ),
    }

    if result.succeeded:
        if result.decoded_text is None:
            raise RuntimeError(
                "Internal transport invariant failed: successful result has no text."
            )
        payload["decoded_scalar_count"] = len(result.decoded_text)

    payload["reasons"] = [
        _reason_to_json_object(reason) for reason in result.reasons
    ]

    return json.dumps(
        payload,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=False,
    )


__all__ = [
    "ByteSpan",
    "ReasonRecord",
    "TransportResult",
    "INVALID_UTF8",
    "UTF8_BOM_FORBIDDEN",
    "SCHEMA_ID",
    "PROFILE_ID",
    "OBSERVATION_KIND",
    "TRANSPORT_DECODED",
    "TRANSPORT_FAILED",
    "inspect_source_bytes",
    "serialize_transport_result",
]

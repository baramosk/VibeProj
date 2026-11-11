"""multipart/form-data 파서.

``cgi`` 모듈은 Python 3.13에서 제거되었으므로 직접 구현한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


class MultipartError(ValueError):
    """multipart 본문을 해석할 수 없을 때 발생한다."""


@dataclass
class Part:
    name: str
    filename: str | None
    content_type: str
    data: bytes


_BOUNDARY_RE = re.compile(r'boundary=(?:"([^"]+)"|([^;\s]+))', re.IGNORECASE)
_PARAM_RE = re.compile(r'(\w+)="((?:[^"\\]|\\.)*)"')


def parse_multipart(body: bytes, content_type: str) -> list[Part]:
    match = _BOUNDARY_RE.search(content_type)
    if match is None:
        raise MultipartError("multipart boundary가 없습니다.")
    boundary = (match.group(1) or match.group(2)).encode("ascii")
    delimiter = b"--" + boundary

    parts: list[Part] = []
    for chunk in body.split(delimiter)[1:]:
        if chunk.startswith(b"--"):          # 종료 구분자
            break
        if chunk.startswith(b"\r\n"):
            chunk = chunk[2:]
        if chunk.endswith(b"\r\n"):
            chunk = chunk[:-2]

        head, sep, data = chunk.partition(b"\r\n\r\n")
        if not sep:
            raise MultipartError("잘못된 multipart 형식입니다.")

        headers: dict[str, str] = {}
        for line in head.decode("utf-8", "replace").split("\r\n"):
            key, _, value = line.partition(":")
            headers[key.strip().lower()] = value.strip()

        params = dict(_PARAM_RE.findall(headers.get("content-disposition", "")))
        if "name" not in params:
            raise MultipartError("Content-Disposition에 name이 없습니다.")
        parts.append(Part(
            name=params["name"],
            filename=params.get("filename"),
            content_type=headers.get("content-type", "application/octet-stream"),
            data=data,
        ))
    return parts

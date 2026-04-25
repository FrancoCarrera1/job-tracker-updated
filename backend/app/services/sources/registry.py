from __future__ import annotations

from typing import Type

_REGISTRY: dict[str, Type] = {}


def register_source(name: str):
    def deco(cls):
        cls.source_kind = name
        _REGISTRY[name] = cls
        return cls

    return deco


def get_source_class(name: str) -> Type | None:
    return _REGISTRY.get(name)


def list_sources() -> list[str]:
    return sorted(_REGISTRY.keys())

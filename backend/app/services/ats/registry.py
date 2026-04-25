from __future__ import annotations

from typing import Type

_REGISTRY: dict[str, Type] = {}


def register(name: str):
    def deco(cls):
        cls.ats_name = name
        _REGISTRY[name] = cls
        return cls

    return deco


def get_handler_class(name: str) -> Type | None:
    return _REGISTRY.get(name)


def list_handlers() -> list[str]:
    return sorted(_REGISTRY.keys())

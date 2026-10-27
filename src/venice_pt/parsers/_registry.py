from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import cast

from venice_pt.contracts.facts import Fact
from venice_pt.parsers.base import ParserContext

ParserFunc = Callable[[bytes, ParserContext], list[Fact]]


def get_parser(parser_path: str) -> ParserFunc:
    module_name, func_name = parser_path.split(":")
    mod = importlib.import_module(module_name)
    func = getattr(mod, func_name)
    return cast(ParserFunc, func)

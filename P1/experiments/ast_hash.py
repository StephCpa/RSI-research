"""AST-normalized within-problem deduplication helper for Python candidates."""
from __future__ import annotations
import ast
import hashlib


def normalized_ast_text(code: str) -> str:
    tree = ast.parse(code)
    return ast.dump(tree, annotate_fields=True, include_attributes=False)


def ast_sha256(code: str) -> str:
    return hashlib.sha256(normalized_ast_text(code).encode("utf-8")).hexdigest()

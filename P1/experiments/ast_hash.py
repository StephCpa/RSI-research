"""Three-level duplication hashes for Python candidates.

raw:
    Exact UTF-8 response text. This is the sampler/cache diagnostic.

strict:
    Parsed AST dump with source positions removed. Comments disappear, but
    docstrings and identifier spellings remain. This preserves the original
    project's AST metric for continuity.

loose:
    AST with module/function/class docstrings removed and function-local
    identifiers alpha-renamed. This treats simple local-variable renames and
    docstring additions as the same solution while preserving global/builtin
    names and program structure.

The loose normalizer is deliberately conservative: it does not attempt general
semantic equivalence.
"""
from __future__ import annotations

import ast
import hashlib


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def raw_sha256(code: str) -> str:
    """Hash the exact candidate text."""
    return _sha256_text(code)


def strict_ast_text(code: str) -> str:
    tree = ast.parse(code)
    return ast.dump(tree, annotate_fields=True, include_attributes=False)


def strict_ast_sha256(code: str) -> str:
    return _sha256_text(strict_ast_text(code))


# Backward-compatible names used elsewhere in the repository.
normalized_ast_text = strict_ast_text
ast_sha256 = strict_ast_sha256


def _strip_docstring(body):
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        return body[1:]
    return body


def _argument_names(args: ast.arguments):
    out = [a.arg for a in getattr(args, "posonlyargs", [])]
    out.extend(a.arg for a in args.args)
    if args.vararg:
        out.append(args.vararg.arg)
    out.extend(a.arg for a in args.kwonlyargs)
    if args.kwarg:
        out.append(args.kwarg.arg)
    return out


class _LocalCollector(ast.NodeVisitor):
    """Collect bindings for one function scope without descending into nested scopes."""

    def __init__(self):
        self.names = []
        self._seen = set()
        self.globals = set()
        self.nonlocals = set()

    def add(self, name):
        if name and name not in self._seen:
            self._seen.add(name)
            self.names.append(name)

    def visit_Global(self, node):
        self.globals.update(node.names)

    def visit_Nonlocal(self, node):
        self.nonlocals.update(node.names)

    def visit_Name(self, node):
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.add(node.id)

    def visit_FunctionDef(self, node):
        self.add(node.name)

    def visit_AsyncFunctionDef(self, node):
        self.add(node.name)

    def visit_ClassDef(self, node):
        self.add(node.name)

    def visit_Lambda(self, node):
        # Nested lexical scope.
        return

    def visit_ExceptHandler(self, node):
        if isinstance(node.name, str):
            self.add(node.name)
        for stmt in node.body:
            self.visit(stmt)


class _LooseNormalizer(ast.NodeTransformer):
    def __init__(self):
        self.scopes = []

    def _lookup(self, name):
        for mapping in reversed(self.scopes):
            if name in mapping:
                return mapping[name]
        return name

    def visit_Module(self, node):
        node.body = _strip_docstring(node.body)
        node.body = [self.visit(x) for x in node.body]
        return node

    def _visit_function(self, node):
        # A nested helper's definition name is a local binding in its parent.
        if self.scopes:
            node.name = self._lookup(node.name)

        # Defaults/decorators execute in the parent scope.
        node.decorator_list = [self.visit(x) for x in node.decorator_list]
        node.args.defaults = [self.visit(x) for x in node.args.defaults]
        node.args.kw_defaults = [
            self.visit(x) if x is not None else None
            for x in node.args.kw_defaults
        ]
        if node.returns is not None:
            node.returns = self.visit(node.returns)

        collector = _LocalCollector()
        for stmt in node.body:
            collector.visit(stmt)

        excluded = collector.globals | collector.nonlocals
        ordered = []
        seen = set()
        for name in _argument_names(node.args) + collector.names:
            if name not in excluded and name not in seen:
                seen.add(name)
                ordered.append(name)
        mapping = {name: f"_v{i}" for i, name in enumerate(ordered)}

        self.scopes.append(mapping)

        args = (
            list(getattr(node.args, "posonlyargs", []))
            + list(node.args.args)
            + list(node.args.kwonlyargs)
        )
        for arg in args:
            arg.arg = self._lookup(arg.arg)
            if arg.annotation is not None:
                arg.annotation = self.visit(arg.annotation)
        if node.args.vararg:
            node.args.vararg.arg = self._lookup(node.args.vararg.arg)
            if node.args.vararg.annotation is not None:
                node.args.vararg.annotation = self.visit(node.args.vararg.annotation)
        if node.args.kwarg:
            node.args.kwarg.arg = self._lookup(node.args.kwarg.arg)
            if node.args.kwarg.annotation is not None:
                node.args.kwarg.annotation = self.visit(node.args.kwarg.annotation)

        node.body = _strip_docstring(node.body)
        node.body = [self.visit(x) for x in node.body]
        self.scopes.pop()
        return node

    def visit_FunctionDef(self, node):
        return self._visit_function(node)

    def visit_AsyncFunctionDef(self, node):
        return self._visit_function(node)

    def visit_Lambda(self, node):
        collector = _LocalCollector()
        collector.visit(node.body)
        ordered = []
        seen = set()
        for name in _argument_names(node.args) + collector.names:
            if name not in seen:
                seen.add(name)
                ordered.append(name)
        mapping = {name: f"_v{i}" for i, name in enumerate(ordered)}
        self.scopes.append(mapping)

        args = (
            list(getattr(node.args, "posonlyargs", []))
            + list(node.args.args)
            + list(node.args.kwonlyargs)
        )
        for arg in args:
            arg.arg = self._lookup(arg.arg)
        if node.args.vararg:
            node.args.vararg.arg = self._lookup(node.args.vararg.arg)
        if node.args.kwarg:
            node.args.kwarg.arg = self._lookup(node.args.kwarg.arg)

        node.body = self.visit(node.body)
        self.scopes.pop()
        return node

    def visit_Name(self, node):
        node.id = self._lookup(node.id)
        return node

    def visit_ExceptHandler(self, node):
        if isinstance(node.name, str):
            node.name = self._lookup(node.name)
        node.type = self.visit(node.type) if node.type is not None else None
        node.body = [self.visit(x) for x in node.body]
        return node

    def visit_Nonlocal(self, node):
        node.names = [self._lookup(x) for x in node.names]
        return node


def loose_ast_text(code: str) -> str:
    tree = ast.parse(code)
    tree = _LooseNormalizer().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.dump(tree, annotate_fields=True, include_attributes=False)


def loose_ast_sha256(code: str) -> str:
    return _sha256_text(loose_ast_text(code))


def hash_triplet(code: str):
    """Return raw/strict/loose hashes. SyntaxError is intentionally propagated."""
    return {
        "raw": raw_sha256(code),
        "strict": strict_ast_sha256(code),
        "loose": loose_ast_sha256(code),
    }

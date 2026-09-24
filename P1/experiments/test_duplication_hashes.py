"""Self-test for the three-level candidate duplication hashes."""
from ast_hash import raw_sha256, strict_ast_sha256, loose_ast_sha256


def eq(a, b):
    return (
        raw_sha256(a) == raw_sha256(b),
        strict_ast_sha256(a) == strict_ast_sha256(b),
        loose_ast_sha256(a) == loose_ast_sha256(b),
    )


base = """def f(xs):
    return [x * 2 for x in xs]
"""
comment = """def f(xs):
    # comment only
    return [x * 2 for x in xs]
"""
rename = """def f(lst):
    return [y * 2 for y in lst]
"""
doc = '''def f(xs):
    """documentation"""
    return [x * 2 for x in xs]
'''
different = """def f(xs):
    return list(map(lambda x: x * 2, xs))
"""

assert eq(base, comment) == (False, True, True)
assert eq(base, rename) == (False, False, True)
assert eq(base, doc) == (False, False, True)
assert eq(base, different) == (False, False, False)

print("DUPLICATION_HASH_SELFTEST: PASS")

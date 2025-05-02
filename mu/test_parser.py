import pytest

from mu.parser import sexpr, MuParserError
from mu.types import SAtom, SGroup, SSeq, SMap, SStr, SMapField, SDoc, SExpr


def parse(expr: str) -> list[SExpr]:
    doc = sexpr(expr, no_spans=False)
    assert str(doc) == expr
    return doc.drop_spans().exprs


def test_parser():
    # Test empty input
    assert parse('') == []

    # Test whitespace handling
    assert parse('  \t\n  ') == []
    assert parse(' a  b \t c \n d ') == [SAtom('a'), SAtom('b'), SAtom('c'), SAtom('d')]

    assert parse('(a b c)') == [SGroup([SAtom('a'), SAtom('b'), SAtom('c')])]
    assert parse('[a b c]') == [SSeq([SAtom('a'), SAtom('b'), SAtom('c')])]
    assert parse('[a, b , c ,d]') == [SSeq([SAtom('a'), SAtom('b'), SAtom('c'), SAtom('d')])]
    
    assert parse('a b c') == [SAtom('a'), SAtom('b'), SAtom('c')]
    assert parse('a b (c d)') == [SAtom('a'), SAtom('b'), SGroup([SAtom('c'), SAtom('d')])]
    assert parse('a b [c d]') == [SAtom('a'), SAtom('b'), SSeq([SAtom('c'), SAtom('d')])]
    assert parse('a b (c d) [e f]') == [SAtom('a'), SAtom('b'), SGroup([SAtom('c'), SAtom('d')]), SSeq([SAtom('e'), SAtom('f')])]

    assert parse('{ a : b }') == [SMap([SMapField(SAtom('a'), SAtom('b'))])]
    assert parse('{ a : b, (a) : 1 }') == [SMap([
        SMapField(SAtom('a'), SAtom('b')),
        SMapField(SGroup([SAtom('a')]), SAtom('1'))
    ])]
    assert parse('{a : b}') == [SMap([SMapField(SAtom('a'), SAtom('b'))])]
    assert parse('{ a : b }') == [SMap([SMapField(SAtom('a'), SAtom('b'))])]
    assert parse('{a : b, c : d}') == [SMap([SMapField(SAtom('a'), SAtom('b')), SMapField(SAtom('c'), SAtom('d'))])]
    assert parse('a (b c) [d e] {f : g}') == [
        SAtom('a'), 
        SGroup([SAtom('b'), SAtom('c')]), 
        SSeq([SAtom('d'), SAtom('e')]), 
        SMap([SMapField(SAtom('f'), SAtom('g'))])]
    assert parse('{}') == [SMap([])]

    assert parse('a "b c"') == [SAtom('a'), SStr('b c')]
    assert parse('a "b c" d') == [SAtom('a'), SStr('b c'), SAtom('d')]
    assert parse('a "b\\"c" d') == [SAtom('a'), SStr('b"c'), SAtom('d')]

    assert parse('a #"b" c') == [SAtom('a'), SStr('b'), SAtom('c')]
    assert parse('a #"" c') == [SAtom('a'), SStr(''), SAtom('c')]
    assert parse('a #x"b""x c') == [SAtom('a'), SStr('b"'), SAtom('c')]
    assert parse('a #tag"b""tag d') == [SAtom('a'), SStr('b"'), SAtom('d')]

    # Test nested structures
    assert parse('(a (b c) [d e])') == [SGroup([SAtom('a'), SGroup([SAtom('b'), SAtom('c')]), SSeq([SAtom('d'), SAtom('e')])])]

    # Test more complex maps
    assert parse('{ a : 1, b : { c : 2, d : [3, 4] } }') == [SMap([
        SMapField(SAtom('a'), SAtom('1')),
        SMapField(SAtom('b'), SMap([
            SMapField(SAtom('c'), SAtom('2')),
            SMapField(SAtom('d'), SSeq([SAtom('3'), SAtom('4')]))
        ]))
    ])]

    # Test string escapes
    assert parse(r'"a\nb\tc\rd\0e\\f\"g"') == [SStr('a\nb\tc\rd\0e\\f"g')]

    # Test raw strings with various delimiters
    assert parse('#delim"a"b"c"delim') == [SStr('a"b"c')]

    # Test comments
    assert parse('a ; this is a comment') == [SAtom('a')]
    assert parse('a ; this is a comment\nb') == [SAtom('a'), SAtom('b')]
    assert parse('a (b ; inline comment\n c) d') == [SAtom('a'), SGroup([SAtom('b'), SAtom('c')]), SAtom('d')]

    # Test empty structures
    assert parse('() [] {}') == [SGroup([]), SSeq([]), SMap([])]

    # Test atoms with special characters
    assert parse('a-b c_d e!f?') == [SAtom('a-b'), SAtom('c_d'), SAtom('e!f?')]

    # Test multiple top-level expressions
    assert parse('a (b c) [d e] {f : g}') == [SAtom('a'), SGroup([SAtom('b'), SAtom('c')]), SSeq([SAtom('d'), SAtom('e')]), SMap([SMapField(SAtom('f'), SAtom('g'))])]

    assert parse('''
    (gradle "kotlin-ref-walker"
        :version "1.0.0"
        :features [(jvm-kotlin-library)]
        :dependencies [
            ;; ":lib-std-base"
        ])
                ''') == [
        SGroup(values=[
            SAtom(value='gradle'),
            SStr(value='kotlin-ref-walker'),
            SAtom(value=':version'),
            SStr(value='1.0.0'),
            SAtom(value=':features'),
            SSeq(values=[SGroup(values=[
                SAtom(value='jvm-kotlin-library')
            ])]),
            SAtom(value=':dependencies'),
            SSeq(values=[])])]
    
#     parse('''
# ; ------------------------------------------------------------------------------
# ; 1. Leading comments, whitespace, and multiple top-level atoms
# ; ------------------------------------------------------------------------------
    
#         ; Indented comment
# a
# abc_123
# a.b.c
# +1_000_000_000
# -123
# 999.9
# 1/2
# +3/4
# -12/100_000
# some!symbol?
# another@symbol
# ->

# ; Some percentages (if supported)
# 0%
# 50%
# 100%
# 3.5%

# ; ------------------------------------------------------------------------------
# ; 2. Nested group testing
# ; ------------------------------------------------------------------------------
# ( ; a group
#   (nested group)
#   [a list inside a group]
#   {
#     map: inside-group,
#     inner: { nested: "map" }
#   }
#   "string in group with an \"escape\" inside"
#   'single-quoted string'
#   #tag"raw string with #tag"tag
# )

# ; ------------------------------------------------------------------------------
# ; 3. Lists with nested structures
# ; ------------------------------------------------------------------------------
# [ ; a list
#   1
#   2
#   3
#   ( group-inside-list )
#   { key: value,  nested: [a b c] }
#   "a string in a list"
#   #raw"some raw string"raw
#   ; trailing comment in list
# ]

# ; ------------------------------------------------------------------------------
# ; 4. Map usage, with various key-value types
# ; ------------------------------------------------------------------------------
# {
#   key1: value1,
#   key2: (some group),
#   key3: [some list],
#   "strKey": "strValue",
#   1: 2,
#   -3: +4,
#   3.14: "pi",
#   #raw"rawKey"raw : #delim"rawValue"delim,
#   ratio: 20/30,
#   big-ratio: 100_000/1_000
# }

# ; ------------------------------------------------------------------------------
# ; 5. More multi-expression top-level
# ; ------------------------------------------------------------------------------
# multi1 multi2 multi3

# ; ------------------------------------------------------------------------------
# ; 6. Empty structures
# ; ------------------------------------------------------------------------------
# () [] {}

# ; ------------------------------------------------------------------------------
# ; 7. Strings with escapes
# ; ------------------------------------------------------------------------------
# escapedString: "a\nb\tc\rd\0e\\f\"g"
# singleQuoted: 'new\nline\tcarriage\rreturn\0slash\\quote\"'

# ; ------------------------------------------------------------------------------
# ; 8. Inline comments in the middle of expressions
# ; ------------------------------------------------------------------------------
# a (b ; inline comment after b
#     d)

# ; Second inline
# a [b ; comment again
#     d]

# ; ------------------------------------------------------------------------------
# ; 9. A final expression with multiple parts
# ; ------------------------------------------------------------------------------
# (final expression)
# ''')
    
def test_parser_errors():
    with pytest.raises(MuParserError):
        parse("(a b")
    with pytest.raises(MuParserError):
        parse("[a b")
    with pytest.raises(MuParserError):
        parse("{a: 1")
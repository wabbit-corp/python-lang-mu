import pytest

from mu.parser import ParseError
from mu.parser import parse as parse_mu
from mu.types import AtomExpr, Expr, GroupExpr, MappingExpr, MappingField, SequenceExpr, SInt, StringExpr


def parse_expr(expr: str) -> list[Expr]:
    doc = parse_mu(expr, preserve_spans=True)
    assert str(doc) == expr
    return doc.drop_spans().exprs


def test_parser():
    # Test empty input
    assert parse_expr("") == []

    # Test whitespace handling
    assert parse_expr("  \t\n  ") == []
    assert parse_expr(" a  b \t c \n d ") == [AtomExpr("a"), AtomExpr("b"), AtomExpr("c"), AtomExpr("d")]

    assert parse_expr("(a b c)") == [GroupExpr([AtomExpr("a"), AtomExpr("b"), AtomExpr("c")])]
    assert parse_expr("[a b c]") == [SequenceExpr([AtomExpr("a"), AtomExpr("b"), AtomExpr("c")])]
    assert parse_expr("[a, b , c ,d]") == [
        SequenceExpr([AtomExpr("a"), AtomExpr("b"), AtomExpr("c"), AtomExpr("d")])
    ]

    assert parse_expr("a b c") == [AtomExpr("a"), AtomExpr("b"), AtomExpr("c")]
    assert parse_expr("a b (c d)") == [
        AtomExpr("a"),
        AtomExpr("b"),
        GroupExpr([AtomExpr("c"), AtomExpr("d")]),
    ]
    assert parse_expr("a b [c d]") == [
        AtomExpr("a"),
        AtomExpr("b"),
        SequenceExpr([AtomExpr("c"), AtomExpr("d")]),
    ]
    assert parse_expr("a b (c d) [e f]") == [
        AtomExpr("a"),
        AtomExpr("b"),
        GroupExpr([AtomExpr("c"), AtomExpr("d")]),
        SequenceExpr([AtomExpr("e"), AtomExpr("f")]),
    ]

    assert parse_expr("{ a : b }") == [MappingExpr([MappingField(AtomExpr("a"), AtomExpr("b"))])]
    assert parse_expr("{ a : b, (a) : 1 }") == [
        MappingExpr(
            [
                MappingField(AtomExpr("a"), AtomExpr("b")),
                MappingField(GroupExpr([AtomExpr("a")]), SInt(1)),
            ]
        )
    ]
    assert parse_expr("{a : b}") == [MappingExpr([MappingField(AtomExpr("a"), AtomExpr("b"))])]
    assert parse_expr("{ a : b }") == [MappingExpr([MappingField(AtomExpr("a"), AtomExpr("b"))])]
    assert parse_expr("{a : b, c : d}") == [
        MappingExpr([MappingField(AtomExpr("a"), AtomExpr("b")), MappingField(AtomExpr("c"), AtomExpr("d"))])
    ]
    assert parse_expr("a (b c) [d e] {f : g}") == [
        AtomExpr("a"),
        GroupExpr([AtomExpr("b"), AtomExpr("c")]),
        SequenceExpr([AtomExpr("d"), AtomExpr("e")]),
        MappingExpr([MappingField(AtomExpr("f"), AtomExpr("g"))]),
    ]
    assert parse_expr("{}") == [MappingExpr([])]

    assert parse_expr('a "b c"') == [AtomExpr("a"), StringExpr("b c")]
    assert parse_expr('a "b c" d') == [AtomExpr("a"), StringExpr("b c"), AtomExpr("d")]
    assert parse_expr('a "b\\"c" d') == [AtomExpr("a"), StringExpr('b"c'), AtomExpr("d")]

    assert parse_expr('a #"b" c') == [AtomExpr("a"), StringExpr("b"), AtomExpr("c")]
    assert parse_expr('a #"" c') == [AtomExpr("a"), StringExpr(""), AtomExpr("c")]
    assert parse_expr('a #x"b""x c') == [AtomExpr("a"), StringExpr('b"'), AtomExpr("c")]
    assert parse_expr('a #tag"b""tag d') == [AtomExpr("a"), StringExpr('b"'), AtomExpr("d")]

    # Test nested structures
    assert parse_expr("(a (b c) [d e])") == [
        GroupExpr(
            [
                AtomExpr("a"),
                GroupExpr([AtomExpr("b"), AtomExpr("c")]),
                SequenceExpr([AtomExpr("d"), AtomExpr("e")]),
            ]
        )
    ]

    # Test more complex maps
    assert parse_expr("{ a : 1, b : { c : 2, d : [3, 4] } }") == [
        MappingExpr(
            [
                MappingField(AtomExpr("a"), SInt(1)),
                MappingField(
                    AtomExpr("b"),
                    MappingExpr(
                        [
                            MappingField(AtomExpr("c"), SInt(2)),
                            MappingField(AtomExpr("d"), SequenceExpr([SInt(3), SInt(4)])),
                        ]
                    ),
                ),
            ]
        )
    ]

    # Test string escapes
    assert parse_expr(r'"a\nb\tc\rd\0e\\f\"g"') == [StringExpr('a\nb\tc\rd\0e\\f"g')]

    # Test raw strings with various delimiters
    assert parse_expr('#delim"a"b"c"delim') == [StringExpr('a"b"c')]

    # Test comments
    assert parse_expr("a ; this is a comment") == [AtomExpr("a")]
    assert parse_expr("a ; this is a comment\nb") == [AtomExpr("a"), AtomExpr("b")]
    assert parse_expr("a (b ; inline comment\n c) d") == [
        AtomExpr("a"),
        GroupExpr([AtomExpr("b"), AtomExpr("c")]),
        AtomExpr("d"),
    ]

    # Test empty structures
    assert parse_expr("() [] {}") == [GroupExpr([]), SequenceExpr([]), MappingExpr([])]

    # Test atoms with special characters
    assert parse_expr("a-b c_d e!f?") == [AtomExpr("a-b"), AtomExpr("c_d"), AtomExpr("e!f?")]

    # Test multiple top-level expressions
    assert parse_expr("a (b c) [d e] {f : g}") == [
        AtomExpr("a"),
        GroupExpr([AtomExpr("b"), AtomExpr("c")]),
        SequenceExpr([AtomExpr("d"), AtomExpr("e")]),
        MappingExpr([MappingField(AtomExpr("f"), AtomExpr("g"))]),
    ]

    assert (
        parse_expr(
            """
    (gradle "kotlin-ref-walker"
        :version "1.0.0"
        :features [(jvm-kotlin-library)]
        :dependencies [
            ;; ":lib-std-base"
        ])
                """
        )
        == [
            GroupExpr(
                values=[
                    AtomExpr(value="gradle"),
                    StringExpr(value="kotlin-ref-walker"),
                    AtomExpr(value=":version"),
                    StringExpr(value="1.0.0"),
                    AtomExpr(value=":features"),
                    SequenceExpr(values=[GroupExpr(values=[AtomExpr(value="jvm-kotlin-library")])]),
                    AtomExpr(value=":dependencies"),
                    SequenceExpr(values=[]),
                ]
            )
        ]
    )


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
    with pytest.raises(ParseError):
        parse_expr("(a b")
    with pytest.raises(ParseError):
        parse_expr("[a b")
    with pytest.raises(ParseError):
        parse_expr("{a: 1")

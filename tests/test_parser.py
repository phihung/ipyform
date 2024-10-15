import json

import pytest
from inline_snapshot import snapshot

from ipyform.entities import Form, Markdown, Param
from ipyform.parser import _extract_title_and_display_mode, _parse_comment, _try_consume_json, parse


@pytest.mark.parametrize(
    "comment, expected_options, expected_config",
    [
        ("@param", None, {}),
        (
            '@param {"type":"string","placeholder":"hi}"}',
            None,
            {"type": "string", "placeholder": "hi}"},
        ),
        ('@param [1, "2", "test]"]', [1, "2", "test]"], {}),
        ('@param [1, ["2"], "test"] {"type":"number"}', [1, ["2"], "test"], {"type": "number"}),
    ],
)
def test_parse_comment(comment, expected_options, expected_config):
    options, config = _parse_comment(comment)
    assert options == expected_options
    assert config == expected_config


@pytest.mark.parametrize(
    "json_str",
    [
        '{"key": "value"}',
        '{"key": "}"}',
        '[1, "2", 3]',
        '[1, "2", {}]',
        '{"key": [1, 2]}',
        '{"key": {"a": "b"}}',
    ],
)
def test_try_consume_json(json_str):
    for before in ["", "   ", '{"aaa":', "}", "]", "{", "[", ' {"key": "v"} ']:
        for after in ["", "   ", " {aaa", "}", "]", ' {"key": "v"}']:
            json_obj, next_idx = _try_consume_json(before + json_str + after, len(before))
            assert json_obj == json.loads(json_str)
            assert next_idx == len(before) + len(json_str)


@pytest.mark.parametrize(
    "json_str",
    [
        '{"key": "value}',
        '[1, "2", {]',
        '{"key": [1, 2]]',
    ],
)
def test_try_consume_json_should_fail(json_str):
    for before in ["", "   ", '{"aaa":', "}", "]", "{", "[", ' {"key": "v"} ']:
        for after in ["", "   ", " {aaa", "}", "]", ' {"key": "v"}']:
            with pytest.raises(ValueError):
                _try_consume_json(before + json_str + after, len(before))


def test_parse_form():
    code = """

# @title My Title
# @markdown My Markdown
a01 = "a"     # @param {"type":"string","placeholder":"hi"}
a02 = False # @param {"type":"boolean"}

# @markdown My Markdown 2
"""
    assert parse(code) == snapshot(
        Form(
            code=[
                "",
                "",
                "# @title My Title",
                "# @markdown My Markdown",
                'a01 = "a"     # @param {"type":"string","placeholder":"hi"}',
                'a02 = False # @param {"type":"boolean"}',
                "",
                "# @markdown My Markdown 2",
            ],
            title="My Title",
            params=[
                Param(
                    code='a01 = "a"     # @param {"type":"string","placeholder":"hi"}',
                    lineno=5,
                    field_type="input",
                    var_type="string",
                    variable="a01",
                    value="a",
                    placeholder="hi",
                ),
                Param(
                    code='a02 = False # @param {"type":"boolean"}',
                    lineno=6,
                    field_type="input",
                    var_type="boolean",
                    variable="a02",
                    value=False,
                ),
            ],
            markdowns=[
                Markdown(code="# @markdown My Markdown", lineno=4, text="My Markdown"),
                Markdown(code="# @markdown My Markdown 2", lineno=8, text="My Markdown 2"),
            ],
            errors=[],
        )
    )


@pytest.mark.parametrize(
    "code, expected",
    [
        (
            'a01 = "a1value"     # @param {"type":"string","placeholder":"hi"}',
            Param(
                code='a01 = "a1value"     # @param {"type":"string","placeholder":"hi"}',
                lineno=1,
                field_type="input",
                var_type="string",
                variable="a01",
                value="a1value",
                placeholder="hi",
            ),
        ),
        (
            'a02 = False # @param {"type":"boolean"}',
            Param(
                code='a02 = False # @param {"type":"boolean"}',
                lineno=1,
                field_type="input",
                var_type="boolean",
                variable="a02",
                value=False,
            ),
        ),
        (
            'a03 = "2024-10-11" # @param {"type":"date"}',
            Param(
                code='a03 = "2024-10-11" # @param {"type":"date"}',
                lineno=1,
                field_type="input",
                var_type="date",
                variable="a03",
                value="2024-10-11",
            ),
        ),
        (
            'a04 = 3 # @param {"type":"number"}',
            Param(
                code='a04 = 3 # @param {"type":"number"}',
                lineno=1,
                field_type="input",
                var_type="number",
                variable="a04",
                value=3,
            ),
        ),
        (
            'a05 = a04 # @param {"type":"raw"}',
            Param(
                code='a05 = a04 # @param {"type":"raw"}',
                lineno=1,
                field_type="input",
                var_type="raw",
                variable="a05",
                value="a04",
            ),
        ),
        (
            'a06 = 11    # @param {"type":"integer"}',
            Param(
                code='a06 = 11    # @param {"type":"integer"}',
                lineno=1,
                field_type="input",
                var_type="integer",
                variable="a06",
                value=11,
            ),
        ),
        (
            "a07 = 70 # @param",
            Param(
                code="a07 = 70 # @param",
                lineno=1,
                field_type="input",
                var_type="raw",
                variable="a07",
                value=70,
            ),
        ),
        (
            "a08 = a01 + 1  # @param",
            Param(
                code="a08 = a01 + 1  # @param",
                lineno=1,
                field_type="input",
                var_type="raw",
                variable="a08",
                value="a01 + 1",
            ),
        ),
        (
            'a11 = a01 # @param [1,"2","a01","1 + 1"] {"type":"raw"}',
            Param(
                code='a11 = a01 # @param [1,"2","a01","1 + 1"] {"type":"raw"}',
                lineno=1,
                field_type="dropdown",
                var_type="raw",
                variable="a11",
                value="a01",
                options=["1", "2", "a01", "1 + 1"],
            ),
        ),
        (
            'a12 = "1" # @param [1,"a]"]',
            Param(
                code='a12 = "1" # @param [1,"a]"]',
                lineno=1,
                field_type="dropdown",
                var_type="string",
                variable="a12",
                value="1",
                options=["1", "a]"],
            ),
        ),
        (
            'a13 = a01 # @param ["1","a01"] {"type":"raw","allow-input":true}',
            Param(
                code='a13 = a01 # @param ["1","a01"] {"type":"raw","allow-input":true}',
                lineno=1,
                field_type="dropdown",
                var_type="raw",
                variable="a13",
                value="a01",
                options=["1", "a01"],
                allow_input=True,
            ),
        ),
        (
            'a14 = "1234" # @param ["1","a01"] {"type":"string","allow-input":true}',
            Param(
                code='a14 = "1234" # @param ["1","a01"] {"type":"string","allow-input":true}',
                lineno=1,
                field_type="dropdown",
                var_type="string",
                variable="a14",
                value="1234",
                options=["1", "a01"],
                allow_input=True,
            ),
        ),
        (
            'a21 = 11 # @param {"type":"slider","min":0,"max":100,"step":1}',
            Param(
                code='a21 = 11 # @param {"type":"slider","min":0,"max":100,"step":1}',
                lineno=1,
                field_type="slider",
                var_type="number",
                variable="a21",
                value=11,
                min=0.0,
                max=100.0,
                step=1.0,
            ),
        ),
        (
            'a22 = 1.4 # @param {"type":"slider","min":1.0,"max":2.0,"step": 0.1}',
            Param(
                code='a22 = 1.4 # @param {"type":"slider","min":1.0,"max":2.0,"step": 0.1}',
                lineno=1,
                field_type="slider",
                var_type="number",
                variable="a22",
                value=1.4,
                min=1.0,
                max=2.0,
                step=0.1,
            ),
        ),
    ],
)
def test_parse_single(code, expected):
    form = parse(code)
    assert len(form.params) == 1
    assert form.params[0] == expected


@pytest.mark.parametrize(
    "code, expected_error_message",
    [
        ("c01 = 1 # @param hello", "Unable to parse @param comment: `hello`"),
        ('c02 = "a" # @param {type:"slider"}', "number"),
        ('c02 = 1 # @param {type:"slider", min: 5, max: 0}', "less"),
        ('c02 = 1 # @param {type:"slider", max: "foo"}', "foo"),
        ('c02 = 103 # @param {type:"slider"}', "Value 103.0 not in range [0, 100]"),
        ('c02 = "ten" # @param {type:"slider"}', "value must be a number. Found: ten"),
        ('c02 = 1 # @param {"type":"slider", foo: "bar"}', "foo"),
        ('c02 = 1 # @param {foo: "bar"}', "foo"),
        ('c02 = 1 # @param [1, 2] {foo: "bar"}', "foo"),
        ('c02 = 1 # @param {type: "foo"}', "foo"),
        ("c02 = 1 # @param {]", "JSON parsing failed"),
        ('c02 = 1 # @param [1, 2] {type: "integer"}', "integer"),
    ],
)
def test_parse_errors(code, expected_error_message):
    form = parse(code)
    assert len(form.params) == 0
    assert len(form.errors) == 1
    assert form.errors[0].code == code
    assert form.errors[0].lineno == 1
    assert expected_error_message in form.errors[0].error


def test_extract_title_and_display_mode_error():
    assert ("hello {]", None) == _extract_title_and_display_mode(["# @title hello {]"])


@pytest.mark.parametrize(
    "code",
    [
        "a = 1",
        "a = 1 # a param",
        "foo(1)  # @param {type: 'slider'}",
        "a.f = 2  # @param {type: 'slider'}",
        "for i in range(10):\n    print(i)  # @param {type: 'slider'}",
    ],
)
def test_parse_ignore(code):
    form = parse(code)
    assert len(form.params) == 0
    assert len(form.errors) == 0
    assert form.code == code.splitlines()

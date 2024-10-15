import re
from datetime import date
from unittest.mock import patch

import pytest
from inline_snapshot import snapshot

from ipyform import env, parser
from ipyform.widgets import FormWidget


@pytest.mark.parametrize(
    "cell,v0, v1,v2",
    [
        # Input
        ('a = 1 # @param {type: "integer"}', 1, "1234", 1234),
        ('a = True # @param {type: "boolean"}', True, False, False),
        ('a = 1 # @param {type: "string"}', "1", "1234", "1234"),
        ('a = 1 # @param {type: "number"}', 1.0, "12.34", 12.34),
        ('a = 1 # @param {type: "raw"}', 1, "1 + 1", 2),
        ('b = 5\na = b + 1 # @param {type: "raw"}', 6, "b * 2", 10),
        ('a = "2024-01-30" # @param {type: "date"}', "2024-01-30", date(2020, 10, 1), "2020-10-01"),
        # Dropdown
        ('a = 1 # @param [1, 2] {type: "raw"}', 1, "2", 2),
        ('b = 2\na = 1 # @param [1, "b + 2"] {type: "raw"}', 1, "b + 2", 4),
        ('a = 1 # @param [1, 2] {type: "string"}', "1", "2", "2"),
        ('a = 3 # @param [1, 2] {type: "raw", "allow-input": true}', 3, "4", 4),
        ('a = 3 # @param [1, 2] {type: "string", "allow-input": true}', "3", "4", "4"),
        # Slider
        ('a = 1 # @param {type: "slider"}', 1, 55, 55),
    ],
)
def test_form_single(cell, v0, v1, v2):
    form_data = parser.parse(cell)
    env = {}
    f = FormWidget(form_data, ns=env)
    assert env["a"] == v0

    get_by_desc(f, "a").value = v1
    assert env["a"] == v2


@patch.object(env, "IN_VSCODE", False)
def test_multiple():
    _run_test_multiple(False)


@patch.object(env, "IN_VSCODE", True)
def test_multiple_vscode():
    _run_test_multiple(True)


def _run_test_multiple(in_vscode):
    cell = """
# @title MyTitle { display-mode: "form" }
# @markdown ### subtitle
a = 1 # @param {type: integer}
# @markdown ### subtitle2
b = a + 1 # @param {type: integer}
"""
    form_data = parser.parse(cell)
    env = {}
    f = FormWidget(form_data, ns=env)
    assert env["a"] == 1
    assert env["b"] == 2

    get_by_desc(f, "a").value = "2"
    assert env["a"] == 2
    assert env["b"] == 3

    f_str = str(f)
    id_ = re.findall(r'id="(.+)"', str(f))

    if not in_vscode:
        f_str = f_str.replace(id_[0], "myid")
        assert f_str == snapshot(
            "FormWidget(children=(VBox(children=(HTML(value='<button onClick=\"code_toggle(\\'myid\\')\" id=\"myid\">Hide/Show Code</button>'), HTML(value='<h2>MyTitle</h2>'), HTML(value='<h3>subtitle</h3>'), Box(children=(Text(value='2', continuous_update=False, description='a', layout=Layout(width='400px'), placeholder='', style=TextStyle(description_width='150px')),), layout=Layout(display='grid', grid_template_columns='auto auto auto')), HTML(value='<h3>subtitle2</h3>'), Box(children=(Text(value='a + 1', continuous_update=False, description='b', layout=Layout(width='400px'), placeholder='', style=TextStyle(description_width='150px')),), layout=Layout(display='grid', grid_template_columns='auto auto auto')), Output())),))"
        )
    else:
        assert f_str == snapshot(
            "FormWidget(children=(VBox(children=(HTML(value=''), HTML(value='<h2>MyTitle</h2>'), HTML(value='<h3>subtitle</h3>'), Box(children=(Text(value='2', continuous_update=False, description='a', layout=Layout(width='400px'), placeholder='', style=TextStyle(description_width='150px')),), layout=Layout(display='grid', grid_template_columns='auto auto auto')), HTML(value='<h3>subtitle2</h3>'), Box(children=(Text(value='a + 1', continuous_update=False, description='b', layout=Layout(width='400px'), placeholder='', style=TextStyle(description_width='150px')),), layout=Layout(display='grid', grid_template_columns='auto auto auto')), Output())),))"
        )


def get_by_desc(elt, desc):
    def recursive(elt, desc):
        if getattr(elt, "description", None) == desc:
            return elt
        for child in getattr(elt, "children", []):
            res = recursive(child, desc)
            if res is not None:
                return res

    if out := recursive(elt, desc):
        return out
    raise ValueError("No element with description %r" % desc)

import pytest
from IPython.testing.globalipapp import get_ipython

from ipyform import env
from ipyform.ipython_ext import (
    CONFIG,
    comment_magic_transformer,
    form,
    form_config,
    load_ipython_extension,
)


def test_form():
    env = {}
    form("--col 1", "foo = 1 # @param", local_ns=env)
    assert env["foo"] == 1


def test_form_with_error(caplog):
    env = {}
    form("--col 1", "foo = 1 # @param [2, 3]", local_ns=env)
    assert env["foo"] == 1
    assert "Error at line 1" in caplog.text


def test_form_config():
    old_config = dict(CONFIG)
    try:
        form_config("--col 13 --auto-detect 1")
        assert CONFIG["auto_detect"] == 1
        assert CONFIG["col"] == 13
    finally:
        CONFIG.update(old_config)


@pytest.mark.parametrize(
    "lines,exp",
    [
        ([""], None),
        (["print('hello')"], None),
        (["%%form", ""], None),
        (["# %%form", ""], None),
        (["#!%%form", "", "a = 1 # @param"], "%%form"),
        (["#!  %%form", ""], "%%form"),
    ],
)
def test_comment_magic_transformer(lines, exp):
    origin = list(lines)
    transformed = comment_magic_transformer(lines)
    assert origin[1:] == transformed[1:]
    assert transformed[0] == (exp or origin[0])


@pytest.mark.parametrize(
    "lines,exp",
    [
        ([""], None),
        (["print('hello')"], None),
        (["%%form", ""], None),
        (["# %%form", ""], None),
        (["", "a = 1 # @param"], ["%%form", "", "a = 1 # @param"]),
        (["#!  %%form", "b=2"], ["%%form", "b=2"]),
    ],
)
def test_comment_magic_transformer_auto_detect(lines, exp):
    old_config = dict(CONFIG)
    try:
        CONFIG["auto_detect"] = True
        origin = list(lines)
        transformed = comment_magic_transformer(lines)
        assert transformed == (exp if exp is not None else origin)
    finally:
        CONFIG.update(old_config)


@pytest.mark.parametrize(
    "lines,exp",
    [
        ([""], None),
        (["print('hello')"], None),
        (["# %%form", ""], None),
        (["#!%%form", "", "a = 1 # @param"], None),
        (["#!  %%form", ""], None),
        (["%%form", "a = 1"], ["a = 1"]),
        (["a=1 # @param", "%%form --col 3", "b=2"], ["a=1 # @param", "b=2"]),
    ],
)
def test_comment_magic_transformer_colab(lines, exp):
    try:
        env.IN_COLAB = True
        origin = list(lines)
        transformed = comment_magic_transformer(lines)
        assert transformed == (exp if exp is not None else origin)
    finally:
        env.IN_COLAB = False


def test_load_ext_colab(ipython):
    try:
        env.IN_COLAB = True
        load_ipython_extension(ipython)

        ipython.run_line_magic("form_config", "--foo 1")
        ipython.run_cell_magic("form", "--foo 1", "a = 1")
    finally:
        env.IN_COLAB = False


def test_load_ext(ipython):
    load_ipython_extension(ipython)

    old_config = dict(CONFIG)
    try:
        ipython.run_line_magic("form_config", "--col 13 --auto-detect 1")
        assert CONFIG["auto_detect"] == 1
        assert CONFIG["col"] == 13
    finally:
        CONFIG.update(old_config)


@pytest.fixture(scope="module")
def ipython():
    ip = get_ipython()
    if ip is None:
        pytest.skip("IPython not available")
    yield ip

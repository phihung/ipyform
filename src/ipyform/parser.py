import ast
from typing import Any, Optional

import chompjs

from ipyform.entities import Form, Markdown, Param, ParamError


def parse(code: str) -> Form:
    """Parses Python code to extract variables assigned with @param annotations."""
    lines = code.splitlines()
    tree = ast.parse(code)
    params, failures = [], []
    for node in tree.body:
        if not _is_valid_assignment(node):
            continue

        line = lines[node.lineno - 1]
        target = node.targets[0]
        value = node.value

        # Ensure the target is a simple variable
        if not isinstance(target, ast.Name):
            continue

        variable = target.id
        comment = _extract_comment(line, node)
        if not comment:
            continue

        # Process the comment for options and config
        try:
            options, config = _parse_comment(comment)
        except ValueError as e:
            failures.append(ParamError(error=str(e), code=line, lineno=node.lineno))
            continue

        # Handle different value types
        if isinstance(value, ast.Constant):
            value = value.value
        else:
            value = ast.unparse(value)  # Convert complex expressions to string

        p = _create_param(
            variable=variable,
            value=value,
            options=options,
            config=config,
            code=line,
            lineno=node.lineno,
        )
        if isinstance(p, ParamError):
            failures.append(p)
        else:
            params.append(p)

    title, display_mode = _extract_title_and_display_mode(lines)
    markdown = _extract_markdown(lines)
    return Form(
        code=lines,
        params=params,
        errors=failures,
        title=title,
        markdowns=markdown,
        display_mode=display_mode or "both",
    )


def _is_valid_assignment(node: ast.AST) -> bool:
    """Checks if the node is a valid assignment with a single target and a one-line statement."""
    return (
        isinstance(node, ast.Assign) and len(node.targets) == 1 and node.lineno == node.end_lineno
    )


def _extract_comment(line: str, node: ast.Assign) -> Optional[str]:
    """Extracts the comment starting with @param from a line."""
    comment_start = line.find("#", node.end_col_offset)

    if comment_start == -1:
        return None

    comment = line[comment_start + 1 :].strip()
    if comment.startswith("@param"):
        return comment
    return None


def _parse_comment(comment: str) -> tuple[Optional[list[str]], dict[str, Any]]:
    """Parses the content of a @param comment to extract options and configuration."""
    comment = comment.removeprefix("@param").strip()
    if not comment:
        return None, {}

    if comment.startswith("{"):
        config, _ = _try_consume_json(comment, 0)
        return None, config

    if comment.startswith("["):
        options, next_i = _try_consume_json(comment, 0)
        # Look for optional config after the options list
        next_i = _skip_whitespace(comment, next_i)
        if next_i < len(comment) and comment[next_i] == "{":
            config, _ = _try_consume_json(comment, next_i)
            return options, config
        else:
            return options, {}

    raise ValueError(f"Unable to parse @param comment: `{comment}`")


def _try_consume_json(s: str, start_idx: int) -> tuple[Any, int]:
    """Attempts to parse a JSON object or list from a string starting at a specified index."""
    first_char = s[start_idx]
    end_char = "}" if first_char == "{" else "]"
    i = start_idx + 1
    while i != -1:
        i = s.find(end_char, i)
        if i != -1:
            try:
                return chompjs.parse_js_object(s[start_idx : i + 1]), i + 1
                # return json.loads(s[start_idx : i + 1]), i + 1
            except ValueError:
                i += 1
    raise ValueError(f"JSON parsing failed for: `{s[start_idx:]}`")


def _extract_title_and_display_mode(lines: list[str]) -> tuple[Optional[str], Optional[str]]:
    """Extracts the title from the first line of the code if it starts with '# '."""
    for line in lines:
        if line.startswith("# @title"):
            title = line.removeprefix("# @title").strip()
            if (i := title.find("{")) != -1:
                try:
                    opt, _ = _try_consume_json(title, i)
                    return title[:i].strip(), opt.get("display-mode")
                except ValueError:
                    pass
            return title, None
    return None, None


def _extract_markdown(lines: list[str]) -> list[Markdown]:
    out = []
    for i, line in enumerate(lines):
        if line.startswith("# @markdown"):
            out.append(
                Markdown(code=line, lineno=i + 1, text=line.removeprefix("# @markdown").strip())
            )
    return out


def _skip_whitespace(s: str, idx: int) -> int:
    """Skips over whitespace in a string and returns the next non-whitespace index."""
    while idx < len(s) and s[idx].isspace():
        idx += 1
    return idx


def _create_param(variable, value, options, config, code, lineno) -> Param:
    """Validate the param. Update inplace with defaullt values. Return error message if any."""

    def _error(msg):
        return ParamError(error=msg, code=code, lineno=lineno)

    field_type = None
    typ_ = config.get("type")

    # Dropdown
    if options is not None:
        field_type = "dropdown"
        if err := _check_properties(config, "Dropdowns", ["type", "allow-input"]):
            return _error(err)
        if typ_ is None:
            typ_ = "string"
        if err := _check_type(typ_, "Dropdowns", ["string", "raw"]):
            return _error(err)
        options = [str(o) for o in options]
        if not config.get("allow-input") and str(value) not in options:
            return _error(f"Value {value} not in options: {options}")

    # Slider
    elif typ_ == "slider":
        field_type = "slider"
        if err := _check_properties(config, "Sliders", ["type", "min", "max", "step"]):
            return _error(err)
        for k, default_v in (("min", 0), ("max", 100), ("step", 1)):
            if k not in config:
                config[k] = default_v
            else:
                try:
                    config[k] = float(config[k])
                except ValueError:
                    return _error(f"{k} must be a number. Found: {config[k]}")
        try:
            value = float(value)
        except ValueError:
            return _error(f"value must be a number. Found: {value}")
        if config["min"] > config["max"]:
            return _error("Min must be less than max")
        if value < config["min"] or value > config["max"]:
            return _error(f"Value {value} not in range [{config['min']}, {config['max']}]")

    # Input
    else:
        field_type = "input"
        if err := _check_properties(config, "Inputs", ["type", "placeholder"]):
            return _error(err)
        if typ_ is None:
            typ_ = "raw"
        if err := _check_type(
            typ_, "Inputs", ["string", "number", "date", "integer", "raw", "boolean"]
        ):
            return _error(err)

    return Param(
        code=code,
        lineno=lineno,
        variable=variable,
        value=value,
        field_type=field_type,
        var_type=typ_ if typ_ != "slider" else "number",
        options=options,
        allow_input=config.get("allow-input", False),
        min=config.get("min"),
        max=config.get("max"),
        step=config.get("step"),
        placeholder=config.get("placeholder"),
    )


def _check_properties(config: dict, elem: str, supported: list[str]) -> Optional[str]:
    """Check if all properties in config are supported."""
    for k in config:
        if k not in supported:
            return f"{elem} only support the following properties: {supported}. Found: {k}"


def _check_type(typ_: str, elem: str, supported: list[str]) -> Optional[str]:
    """Check if value is of a supported type."""
    if typ_ not in supported:
        return f"{elem} only support the following types: {supported}. Found: {typ_}"

import logging
import re

from IPython import InteractiveShell
from IPython.core.magic import needs_local_scope, register_cell_magic, register_line_magic
from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring
from IPython.display import HTML, display

from ipyform import env, parser
from ipyform.widgets import FormWidget

logger = logging.getLogger(__package__)


CONFIG = {
    "col": 1,
    "auto_detect": False,
}


def load_ipython_extension(ipython: InteractiveShell):
    if env.IN_COLAB:
        _register_colab()
        return

    ipython.input_transformers_cleanup.append(comment_magic_transformer)
    display(HTML(COLLAPSE_CODE_SCRIPT))

    register_line_magic(form_config)
    register_cell_magic(form)


def _register_colab():
    @register_cell_magic
    def form(args_str, cell):  # pragma: no cover
        logger.warning(
            "This should not be called. Try remove `%%form` line. Please create a github issue."
        )

    @register_line_magic
    def form_config(line):  # pragma: no cover
        ...


@magic_arguments()
@argument("--col", type=int, default=None, help="Number of columns")
@needs_local_scope
def form(args_str, cell, local_ns):
    args = parse_argstring(form, args_str)
    form_data = parser.parse(cell)
    for err in form_data.errors:
        logger.warning(f"Error at line {err.lineno}. {err.error}")
    col = args.col or CONFIG.get("col", 1)
    layout = dict(display="grid", grid_template_columns="auto " * col)
    return FormWidget(form_data, layout=layout, ns=local_ns)


@magic_arguments()
@argument("--auto-detect", type=bool, default=False, help="Auto detect form")
@argument("-c", "--col", type=int, default=1, help="Number of columns")
def form_config(line):
    args = parse_argstring(form_config, line)
    CONFIG["auto_detect"] = args.auto_detect
    CONFIG["col"] = args.col


def comment_magic_transformer(lines: list[str]):
    """Silently transform the code cell before further processing.

    In COLAB:
     - Remove `%%form` and `%%form_config` lines.

    Other IDE:
     - Transform `#! %%form` to `%%form`

    In auto_detection mode:
     - Auto add `%%form` to the first line if `# @param` is found.

    The use of `#! %%form` allows Pylance to only see python code and not the magic, which would otherwise confuse it, and cause it to be disabled.
    """
    if env.IN_COLAB:
        return [line for line in lines if not line.startswith(("%%form", "%%form_config"))]

    out = list(lines)
    for i, line in enumerate(lines):
        if re.match(r"^#!\s*%%form", line):
            out = list(lines)
            out[i] = re.sub(r"^#!\s*", "", line)
            return out

    if CONFIG["auto_detect"] and any("# @param" in line for line in lines):
        return ["%%form"] + lines
    return lines


COLLAPSE_CODE_SCRIPT = """
<script>
function code_toggle(id) {
    var cells = document.querySelectorAll(".jp-CodeCell");
    for (var cell of cells) {
        if (cell.querySelector("#" + id) !== null) {
            var div = cell.querySelector(".jp-InputArea");
            if (div.style.display === "none") {
                div.style.display = "block";
            } else {
                div.style.display = "none";
            }
        }
    }
}
</script>
"""

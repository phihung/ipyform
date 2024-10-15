import uuid
from dataclasses import dataclass
from datetime import date

import ipywidgets as w
import markdown
from IPython.display import HTML, display

from ipyform import env
from ipyform.entities import Form, Param


@dataclass
class Field:
    param: Param
    widget: w.Widget

    def str_value(self) -> str:
        v = self.widget.value
        typ = self.param.var_type
        if typ in ("boolean", "number", "integer", "raw"):
            return str(v)
        elif typ == "date":
            return f'"{v.isoformat()}"'
        elif typ == "string":
            return f'"""{v}"""'
        else:  # pragma: no cover
            raise ValueError(f"Unknown type: {typ}")


def param_to_field(p: Param) -> Field:
    kwargs = dict(
        description=p.variable,
        value=str(p.value),
        style={"description_width": "150px"},
        layout=dict(width="400px"),
    )
    w_field = None
    if p.field_type == "dropdown":
        if p.allow_input:
            w_field = w.Combobox(options=p.options, continuous_update=False, **kwargs)
        else:
            w_field = w.Dropdown(options=p.options, **kwargs)
    elif p.field_type == "slider":
        kwargs["value"] = p.value
        w_field = w.FloatSlider(
            min=p.min, max=p.max, step=p.step, continuous_update=False, **kwargs
        )
    elif p.field_type == "input":
        if p.var_type == "boolean":
            kwargs["value"] = p.value
            w_field = w.Checkbox(**kwargs)
        elif p.var_type == "date":
            kwargs["value"] = date.fromisoformat(p.value)
            w_field = w.DatePicker(**kwargs)
        else:
            w_field = w.Text(**kwargs, continuous_update=False, placeholder=p.placeholder or "")
    else:  # pragma: no cover
        raise ValueError(f"Unknown field type: {p.field_type}")
    return Field(param=p, widget=w_field)


class FormWidget(w.Box):
    def __init__(
        self,
        data: Form,
        ns: dict = globals(),
        layout=dict(display="grid", grid_template_columns="auto auto auto"),
    ):
        self.data = data
        self.fields = [param_to_field(p) for p in data.params]
        self.output = w.Output()
        self.ns = ns
        elems = []

        # Hide code button
        btn, code_collapse = hide_show_code_button()
        elems.append(btn)

        # Title
        if data.title:
            title = (
                markdown.markdown(data.title)
                if data.title.startswith("#")
                else f"<h2>{data.title}</h2>"
            )
            elems.append(w.HTML(title))

        # Markdown and code
        i_prev = 0
        for md in data.markdowns:
            fields = [f for f in self.fields if i_prev <= f.param.lineno < md.lineno]
            if fields:
                elems.append(w.Box([f.widget for f in fields], layout=layout))
            elems.append(w.HTML(markdown.markdown(md.text)))
            i_prev = md.lineno
        fields = [f for f in self.fields if f.param.lineno >= i_prev]
        elems.append(w.Box([f.widget for f in fields], layout=layout))
        elems.append(self.output)

        super().__init__([w.VBox(elems)])
        for f in self.fields:
            f.widget.observe(self._rerun, names="value")
        self._rerun(None)
        if data.display_mode == "form":
            code_collapse()

    def _rerun(self, evt):
        codes = list(self.data.code)
        for f in self.fields:
            codes[f.param.lineno - 1] = f"{f.param.variable} = {f.str_value()}"
        self.output.clear_output()
        with self.output:
            exec("\n".join(codes), None, self.ns)


def hide_show_code_button():
    if env.IN_VSCODE:
        return w.HTML(""), lambda: None
    id_ = "a" + str(uuid.uuid1())[:8]
    script = f"""<button onClick="code_toggle('{id_}')" id="{id_}">Hide/Show Code</button>"""
    return w.HTML(script), lambda: display(
        HTML(f"<script>setTimeout(function() {{ code_toggle('{id_}') }}, 1000);</script>")
    )

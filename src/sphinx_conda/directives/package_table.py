from typing import TYPE_CHECKING, List, cast

import docutils.parsers.rst.directives as directives
from docutils import nodes
from docutils.parsers.rst.directives.tables import ListTable, align
from sphinx import addnodes
from sphinx.util.docutils import SphinxDirective

from ..model import CondaPackage

if TYPE_CHECKING:
    from ..domain import CondaDomain


class PackageListDirective(ListTable, SphinxDirective):

    option_spec = {
        "width": directives.length_or_percentage_or_unitless,
        "widths": directives.value_or(("auto",), directives.positive_int_list),
        "class": directives.class_option,
        "name": directives.unchanged,
        "align": align,
        # dependencies are either:
        #   explicit: included in the environment.yaml
        #   implicit: only in the lockfile - a dependency of an explicit package
        # these flags can be used to show/hide them in the list
        "hide-implicit": directives.flag,
        "hide-explicit": directives.flag,
    }

    def find_packages(self) -> List[CondaPackage]:
        env_obj = None
        parent = cast(nodes.Element, self.state.parent)
        while parent:
            if parent.get("domain") == "conda" and parent["objtype"] == "environment":
                env_obj = cast(addnodes.desc, parent)
                break
            parent = parent.parent
        if env_obj:
            domain = cast("CondaDomain", self.env.get_domain("conda"))
            idx = cast(str, env_obj["names"][-1])
            pkgs = domain.get_environment_packages(idx)
            return pkgs
        else:
            raise ValueError("Not called from within a conda:environment directive")

    def run(self):
        table_data = []
        headers = [nodes.Text("Name"), nodes.Text("Version"), nodes.Text("Build")]
        table_data.append(headers)

        pkgs = self.find_packages()
        if "hide-implicit" in self.options:
            pkgs = [x for x in pkgs if x.explicit is True]

        if "hide-explicit" in self.options:
            pkgs = [x for x in pkgs if x.explicit is False]
        for p in sorted(pkgs):
            table_data.append(
                [nodes.Text(p.name), nodes.Text(p.version), nodes.Text(p.build)]
            )

        title, messages = self.make_title()

        header_rows = 1
        stub_columns = 0
        col_widths = self.get_column_widths(3)
        table_node = self.build_table_from_list(
            table_data, col_widths, header_rows, stub_columns
        )
        if "align" in self.options:
            table_node["align"] = self.options.get("align")
        table_node["classes"] += self.options.get("class", [])
        self.set_table_width(table_node)
        self.add_name(table_node)
        if title:
            table_node.insert(0, title)
        return [table_node] + messages

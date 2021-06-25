import os
from collections import defaultdict
from pathlib import Path
from typing import (
    Any,
    Dict,
    Generator,
    Iterator,
    List,
    NamedTuple,
    Optional,
    Tuple,
    Union,
    cast,
)

import docutils.parsers.rst.directives as directives
from docutils.parsers.rst.directives.tables import ListTable
import yaml
from docutils import nodes
from icecream import ic
from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, Index, ObjType
from sphinx.environment import BuildEnvironment
from sphinx.ext.viewcode import is_supported_builder, viewcode_anchor
from sphinx.locale import _
from sphinx.roles import XRefRole
from sphinx.util import logger, status_iterator
from sphinx.util.docutils import SphinxDirective
from docutils.parsers.rst.states import Body

from .model import CondaLockfile, CondaPackage, CondaYamlfile, Environment
from .util import object_desc, split

OUTPUT_DIR = Path("_environments")


def create_field(name: str, *args: Any) -> nodes.field:
    body = nodes.field_body()
    for arg in args:
        if isinstance(arg, str):
            body += nodes.Text(arg)
        else:
            body += arg
    field = nodes.field()
    field += nodes.field_name(text=name)
    field += body
    return field


class PackageListDirective(ListTable, SphinxDirective):
    def find_packages(self) -> List[CondaPackage]:
        env_obj = None
        parent = cast(nodes.Element, self.state.parent)
        while parent:
            if parent.get("domain") == "conda" and parent["objtype"] == "environment":
                env_obj = cast(addnodes.desc, parent)
                break
            parent = parent.parent
        if env_obj:
            domain = cast(CondaDomain, self.env.get_domain("conda"))
            idx = cast(str, env_obj["names"][-1])
            pkgs = domain.get_environment_packages(idx)
            return pkgs
        else:
            raise ValueError("Not called from within a conda:environment directive")

    def run(self):
        ic(self.option_spec)
        table_data = []
        headers = [nodes.Text("Name"), nodes.Text("Version"), nodes.Text("Build")]
        table_data.append(headers)

        for p in self.find_packages():
            table_data.append(
                [nodes.Text(p.name), nodes.Text(p.version), nodes.Text(p.build)]
            )

        title, messages = self.make_title()
        node = nodes.Element()  # anonymous container for parsing

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


# class PackageListDirective(SphinxDirective):
#     required_arguments = 0
#     has_content = True
#     option_spec = {}

#     def run(self) -> List[nodes.Node]:
#         env_obj = None
#         parent = cast(nodes.Element, self.state.parent)
#         while parent:
#             if parent.get("domain") == "conda" and parent["objtype"] == "environment":
#                 env_obj = cast(addnodes.desc, parent)
#                 break
#             parent = parent.parent
#         if env_obj:
#             domain = cast(CondaDomain, self.env.get_domain("conda"))
#             idx = cast(str, env_obj["names"][-1])
#             pkgs = domain.get_environment_packages(idx)
#             if pkgs:
#                 # # adapted from docutils.parsers.rst.directives.tables.ListTable
#                 # table = nodes.table()
#                 # table["classes"] += ["colwidths-auto"]
#                 # tgroup = nodes.tgroup(cols=3)
#                 # table += tgroup

#                 # header = nodes.thead()
#                 # pkg_table = nodes.tbody()

#                 # rows = []
#                 # for j in range(5):
#                 #     row_node = nodes.row()
#                 #     row_node.extend(
#                 #         [nodes.entry("", nodes.Text("hello")) for i in range(3)]
#                 #     )
#                 #     rows.append(row_node)

#                 # pkg_table.extend(rows)
#                 # # pkg_table += [
#                 # #     nodes.row("", nodes.Text(f"{p.name} {p.version}")) for p in pkgs
#                 # # ]
#                 # table += [header, pkg_table]
#                 # return [table]


#                 # table = nodes.table()
#                 # table["classes"] += ["colwidths-auto"]

#                 # tgroup = nodes.tgroup(cols=3)
#                 # table += tgroup

#                 # for column in ["Package", "Version", "Build"]:
#                 #     colspec = nodes.colspec()
#                 #     tgroup += colspec

#                 # thead = nodes.thead()
#                 # row = nodes.row()
#                 # heads = []
#                 # for i in range(2):
#                 #     entry = nodes.entry()
#                 #     entry += nodes.Text(f"Hey {i}")
#                 #     heads.append(entry)
#                 # row.extend(heads)
#                 # thead += row

#                 # tbody = nodes.tbody()
#                 # row = nodes.row()
#                 # entry = nodes.entry()
#                 # entry += nodes.Text("Hey content")

#                 # row += entry
#                 # tbody += row
#                 # tgroup += thead
#                 # tgroup += tbody

#                 return [table]

#             else:
#                 return [nodes.Text("Packages: " + str(ic(pkgs)))]
#         else:
#             return [nodes.Text("No environment found in document heirarchy")]


class CondaEnvironmentDirective(ObjectDescription[Environment]):
    required_arguments = 1
    final_argument_whitespace = True
    has_content = True
    objtype = "environment"
    option_spec = {
        "envfile": directives.path,
        "lockfile": directives.path,
        "hidepackages": directives.flag,
        "hidedeps": directives.flag,
    }

    def rel_path(self, path: Path) -> Path:
        """Resolve a path relative to this directive."""
        return (Path(self.env.doc2path(self.env.docname)).parent / path).resolve()

    def handle_signature(
        self, sig: str, signode: addnodes.desc_signature
    ) -> Environment:
        # create the environment signature in the document
        signode += addnodes.desc_annotation(text=self.objtype + " ")
        signode += addnodes.desc_name(text=sig)
        # add a link to the source code
        pagename = (OUTPUT_DIR / sig).as_posix()
        anchor = viewcode_anchor(
            reftarget=pagename, refid=signode.get("fullname"), refdoc=self.env.docname
        )
        signode += anchor

        # add the name of the environment to the parent
        # object so we can reference it from other directives
        signode.parent["names"].append("{}.{}".format("environment", sig))

        environment = Environment(
            name=sig,
            yamlfile=self.rel_path(Path(self.options.get("envfile"))),
            lockfile=self.rel_path(Path(self.options.get("lockfile"))),
        )
        return environment

    # def transform_content(self, contentnode: addnodes.desc_content) -> None:
    #     pkgs = list(sorted(self.environment.lockfile.packages, key=lambda x: x.name))
    #     already_shown: List[CondaPackage] = []
    #     if "hidepackages" not in self.options:
    #         contentnode += nodes.rubric(text="Packages")
    #         fields = nodes.field_list()
    #         for spec in self.env_obj.dependencies:
    #             pkg_name, _ = split(spec, "=", 1)
    #             print("pkg_name", pkg_name)
    #             pkg = [p for p in pkgs if p.name == pkg_name][0]
    #             field = create_field(pkg_name, pkg.version)
    #             fields += field
    #             already_shown.append(pkg)
    #         contentnode += fields

    #         if "hidedeps" not in self.options:
    #             contentnode += nodes.rubric(text="Dependencies")
    #             fields = nodes.field_list()
    #             for pkg in pkgs:
    #                 if pkg in already_shown:
    #                     continue
    #                 field = create_field(pkg.name, pkg.version)
    #                 fields += field
    #             contentnode += fields

    def add_target_and_index(
        self, name: Environment, sig: str, signode: addnodes.desc_signature
    ):
        # the super method has signature (name, sig, signode)
        # but really we know name to be an environment obj
        signode["ids"].append("environment" + "-" + sig)
        signode["_conda_yamlfile"] = str(name.yamlfile)
        signode["_conda_lockfile"] = str(name.lockfile)
        domain = cast(CondaDomain, self.env.get_domain("conda"))
        domain.add_environment(name, self.env.docname)


def collect_pages(
    app: Sphinx,
) -> Generator[Tuple[str, Dict[str, Any], str], None, None]:
    """Generate source pages for all environments.

    Similar to `sphinx.ext.autodoc`, here we generate files that contain
    the source code (environment and lock files) of each named
    environment, outputting to `/_environments/[env_name].html`.
    """
    env = app.builder.env
    if not is_supported_builder(app.builder):
        return
    urito = app.builder.get_relative_uri

    domain = cast(CondaDomain, env.get_domain("conda"))
    env_objs = list(domain.get_objects())

    for env_obj in status_iterator(
        env_objs,
        "generating environment pages... ",
        "blue",
        len(env_objs),
        app.verbosity,
        stringify_func=lambda x: x.name,
    ):
        # construct a page name for the highlighted source
        env = domain.get_environment(env_obj.name)
        pagename = (OUTPUT_DIR / env.name).as_posix()
        backlink = urito(pagename, env_obj.docname) + "#" + env_obj.anchor
        parents = []
        context = {
            "parents": parents,
            "title": env.name,
            "name": env.name,
            "doc_loc": backlink,
        }
        if env.yamlfile:
            context.update(
                {
                    "env_filename": env.yamlfile.name,
                    "env_source": open(env.yamlfile).read(),
                }
            )
        if env.lockfile:
            context.update(
                {
                    "lock_filename": env.lockfile.name,
                    "lock_source": open(env.lockfile).read(),
                }
            )
        yield (pagename, context, "environment.html")

    context = {"environments": env_objs}
    yield (
        (OUTPUT_DIR / "index").as_posix(),
        context,
        "environment_index.html",
    )


# class CondaPackageDirective(SphinxDirective):
#     def run(self):
#         return nodes.title("Hello")


# class CondaEnvironmentIndex(Index):
#     name = "conda-environment"
#     localname = "Environment Index"
#     shortname = "Environment"

#     def generate(self, docnames=None):
#         content = defaultdict(list)

#         # sort the list of environments in alphabetical order
#         environments = [x for x in self.domain.get_objects() if x[2] == "environment"]
#         print("environments", environments)
#         environments = sorted(environments, key=lambda environment: environment[0])

#         # generate the expected output, shown below, from the above using the
#         # first letter of the environment as a key to group thing
#         #
#         # name, subtype, docname, anchor, extra, qualifier, description
#         for name, dispname, typ, docname, anchor, _ in environments:
#             content[dispname[0].lower()].append(
#                 (dispname, 0, docname, anchor, docname, "", typ)
#             )

#         # convert the dict to the sorted list of tuples expected
#         content = sorted(content.items())

#         return content, True


class CondaPackageIndex(Index):
    """A custom index that creates an package matrix."""

    name = "packages"
    localname = "Package Index"
    shortname = "packages"

    def generate(self, docnames=None):
        content = defaultdict(list)
        domain = cast(CondaDomain, self.domain)

        for env_obj in domain.get_objects():
            packages = domain.get_environment_packages(env_obj.name)
            for pkg in packages:
                content[pkg.name].append(
                    (
                        env_obj.display_name,
                        0,
                        env_obj.docname,
                        env_obj.anchor,
                        env_obj.type,  # show Requirement or Dependency
                        "version",
                        pkg.version,
                    )
                )

        # convert the dict to the sorted list of tuples expected
        content = sorted(content.items())
        return content, True


class CondaDomain(Domain):
    name = "conda"
    label = "Conda"
    roles = {
        "ref": XRefRole(),
    }
    directives = {
        "environment": CondaEnvironmentDirective,
        "packagelist": PackageListDirective,
        # "package": CondaPackageDirective,
    }
    # indices = {CondaEnvironmentIndex, CondaPackageIndex}
    indices = {CondaPackageIndex}
    initial_data = {
        "environment_refs": [],
        "environments": {},
        "environment_packages": {},
    }
    object_types: Dict[str, ObjType] = {
        "environment": ObjType("environment", "environment", "obj")
    }

    def get_objects(self) -> Iterator[object_desc]:
        for obj in self.data["environment_refs"]:
            yield obj

    def add_environment(self, env: Environment, docname: str):
        idx = "{}.{}".format("environment", env.name)
        anchor = "environment-{}".format(env.name)

        packages: Dict[str, CondaPackage] = {}
        if env.yamlfile:
            yaml_obj = CondaYamlfile.load(env.yamlfile)
            for spec in yaml_obj.dependencies:
                pkg_name, version = split(spec, "=", 1)
                packages[pkg_name] = CondaPackage(name=pkg_name, version=version)
        if env.lockfile:
            lock_obj = CondaLockfile.load(env.lockfile)
            for pkg in lock_obj.packages:
                packages[pkg.name] = pkg

        self.data["environment_packages"][idx] = list(packages.values())
        obj = object_desc(idx, env.name, "Environment", docname, anchor, 0)
        self.data["environment_refs"].append(obj)
        self.data["environments"][idx] = env

    def get_environment_packages(self, idx: str) -> List[CondaPackage]:
        return self.data["environment_packages"][idx]

    def get_environment(self, idx: str) -> Environment:
        return self.data["environments"][idx]


def setup(app: Sphinx):
    app.add_domain(CondaDomain)
    app.connect("html-collect-pages", collect_pages)
    # app.connect("object-description-transform", obj_transform)

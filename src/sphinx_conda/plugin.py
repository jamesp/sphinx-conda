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
from sphinx.environment import BuildEnvironment
import yaml
from docutils import nodes
from icecream import ic

from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, Index, ObjType
from sphinx.ext.viewcode import is_supported_builder, viewcode_anchor
from sphinx.locale import _
from sphinx.roles import XRefRole
from sphinx.util import logger, status_iterator
from sphinx.util.docutils import SphinxDirective

from .util import object_desc, split
from .model import Environment, CondaLockfile, CondaPackage, CondaYamlfile


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

        # yaml_obj, lock_obj = None, None
        # if "envfile" in self.options:
        #     _, env_file = self.env.relfn2path(self.options.get("envfile"))
        #     yaml_obj = CondaYamlfile.load(env_file)
        # if "lockfile" in self.options:
        #     _, lockfile = self.env.relfn2path(self.options.get("lockfile"))
        #     lock_obj = CondaLockfile.load(lockfile)
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
        domain = cast(CondaDomain, self.env.get_domain("conda"))
        domain.add_environment(name, self.env.docname)


def collect_pages(
    app: Sphinx,
) -> Generator[Tuple[str, Dict[str, Any], str], None, None]:
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
                        env_obj.type,
                        "",
                        pkg.version,
                    )
                )

        # environments = {
        #     name: (dispname, typ, docname, anchor)
        #     for name, dispname, typ, docname, anchor, _ in domain.get_objects()
        # }
        # environment_packages = domain.get_environment_packages(name)
        # package_environments = defaultdict(list)

        # # flip from environment_packages to package_environments
        # for environment_name, packages in environment_packages.items():
        #     for package in packages:
        #         package_environments[package].append(environment_name)

        # # convert the mapping of package to environments to produce the expected
        # # output, shown below, using the package name as a key to group
        # #
        # # name, subtype, docname, anchor, extra, qualifier, description
        # for package, environment_names in package_environments.items():
        #     for environment_name in environment_names:
        #         dispname, typ, docname, anchor = environments[environment_name]
        #         content[package].append(
        #             (
        #                 dispname,
        #                 0,
        #                 docname,
        #                 anchor,
        #                 typ,
        #                 "",
        #                 environment_packages[environment_name][package].version,
        #             )
        #         )

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

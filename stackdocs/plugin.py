from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

import docutils.parsers.rst.directives as directives
import yaml
from docutils import nodes
from pydantic import BaseModel
from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, Index, ObjType
from sphinx.ext.viewcode import is_supported_builder, viewcode_anchor
from sphinx.locale import _
from sphinx.roles import XRefRole
from sphinx.util import status_iterator
from sphinx.util.docutils import SphinxDirective

from .util import object_desc, split

ENVS_DIR = Path("environments")
OUTPUT_DIRNAME = "_environments"


class CondaEnvironmentYaml(BaseModel):
    name: str
    dependencies: list[str]

    @classmethod
    def load(cls, name: str) -> "CondaEnvironmentYaml":
        filename = cls.filename(name)
        if not filename.exists():
            raise FileNotFoundError(f"Environment file {filename} doesn't exist")
        with open(filename, "r") as fh:
            raw = yaml.safe_load(fh)
            obj = CondaEnvironmentYaml(**raw)
        return obj

    @classmethod
    def filename(cls, name: str) -> Path:
        return ENVS_DIR / f"{name}.yml"


class CondaPackage(BaseModel):
    name: str
    version: Optional[str]
    build: Optional[str]
    url: Optional[str]
    md5: Optional[str]

    @classmethod
    def from_url(cls, url: str) -> "CondaPackage":
        url, md5 = split(url, "#", 1)
        package = Path(url).name.replace(".conda", "").replace(".tar.bz2", "")
        # packages are named something like hyphenated-name-version-build
        # so the last 2 hyphens need to be split on.
        # so we reverse the string before splitting into 3, then reverse back
        strap = split(package[::-1], "-", 2)
        build, version, name = [p[::-1] for p in strap]
        return cls(name=name, version=version, build=build, url=url, md5=md5)


class CondaLockfile(BaseModel):
    packages: list[CondaPackage]

    @classmethod
    def load(cls, name: str) -> "CondaLockfile":
        filename = cls.filename(name)
        if not filename.exists():
            raise FileNotFoundError(f"Environment lockfile {filename} doesn't exist")
        with open(filename, "r") as fh:
            pkgs = []
            for line in fh:
                line = line.strip()
                if line.startswith("#"):
                    continue
                if line.upper() == "@EXPLICIT":
                    continue
                pkgs.append(CondaPackage.from_url(line))
        return CondaLockfile(packages=pkgs)

    @classmethod
    def filename(cls, name: str) -> Path:
        return ENVS_DIR / f"{name}.lock"


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


class CondaEnvironmentDirective(ObjectDescription):
    required_arguments = 1
    final_argument_whitespace = True
    has_content = True
    objtype = "environment"
    sig: str

    env_obj: CondaEnvironmentYaml

    option_spec = {"hidepackages": directives.flag, "hidedeps": directives.flag}

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        self.sig = sig
        self.env_obj = CondaEnvironmentYaml.load(sig)
        self.lockfile = CondaLockfile.load(sig)
        signode += addnodes.desc_annotation(text=self.objtype + " ")
        signode += addnodes.desc_name(text=self.env_obj.name)
        # add a link to the source code
        pagename = str(Path(OUTPUT_DIRNAME) / "environment" / sig)
        signode += viewcode_anchor(
            reftarget=pagename, refid=signode.get("fullname"), refdoc=self.env.docname
        )
        return sig

    def transform_content(self, contentnode: addnodes.desc_content) -> None:
        pkgs = list(sorted(self.lockfile.packages, key=lambda x: x.name))
        alread_shown = []
        if "hidepackages" not in self.options:
            contentnode += nodes.rubric(text="Packages")
            fields = nodes.field_list()
            for spec in self.env_obj.dependencies:
                pkg_name, _ = split(spec, "=", 1)
                print("pkg_name", pkg_name)
                pkg = [p for p in pkgs if p.name == pkg_name][0]
                field = create_field(pkg_name, pkg.version)
                fields += field
                alread_shown.append(pkg)
            contentnode += fields

            if "hidedeps" not in self.options:
                contentnode += nodes.rubric(text="Dependencies")
                fields = nodes.field_list()
                for pkg in pkgs:
                    if pkg in alread_shown:
                        continue
                    field = create_field(pkg.name, pkg.version)
                    fields += field
                contentnode += fields

    def add_target_and_index(self, name_cls, sig, signode):
        signode["ids"].append("environment" + "-" + sig)
        domain = self.env.get_domain("conda")

        domain.add_environment(sig, self.lockfile.packages)  # type: ignore


def collect_pages(
    app: Sphinx,
) -> Generator[Tuple[str, Dict[str, Any], str], None, None]:
    env = app.builder.env
    if not is_supported_builder(app.builder):
        return
    urito = app.builder.get_relative_uri

    environments = [object_desc(*x) for x in env.get_domain("conda").get_objects()]
    for environment in status_iterator(
        environments,
        "generating environment pages... ",
        "blue",
        len(environments),
        app.verbosity,
        lambda x: x[0],
    ):
        # construct a page name for the highlighted source
        pagename = str(Path(OUTPUT_DIRNAME) / environment.name.replace(".", "/"))
        backlink = urito(pagename, environment.docname) + "#" + environment.anchor
        parents = []
        env_file = CondaEnvironmentYaml.filename(environment.display_name)
        lock_file = CondaLockfile.filename(environment.display_name)
        context = {
            "parents": parents,
            "title": environment.name,
            "env": CondaEnvironmentYaml.load(environment.display_name),
            "env_filename": env_file,
            "lock_filename": lock_file,
            "env_source": open(env_file, "r").read(),
            "lock_source": open(lock_file, "r").read(),
            "doc_loc": backlink,
        }
        yield (pagename, context, "environment.html")

    context = {"environments": [e for e in environments]}
    yield (
        str(Path(OUTPUT_DIRNAME) / "environment/index"),
        context,
        "environment_index.html",
    )


class CondaPackageDirective(SphinxDirective):
    def run(self):
        return nodes.title("Hello")


class CondaEnvironmentIndex(Index):
    name = "conda-environment"
    localname = "Environment Index"
    shortname = "Environment"

    def generate(self, docnames=None):
        content = defaultdict(list)

        # sort the list of environments in alphabetical order
        environments = [x for x in self.domain.get_objects() if x[2] == "environment"]
        print("environments", environments)
        environments = sorted(environments, key=lambda environment: environment[0])

        # generate the expected output, shown below, from the above using the
        # first letter of the environment as a key to group thing
        #
        # name, subtype, docname, anchor, extra, qualifier, description
        for name, dispname, typ, docname, anchor, _ in environments:
            content[dispname[0].lower()].append(
                (dispname, 0, docname, anchor, docname, "", typ)
            )

        # convert the dict to the sorted list of tuples expected
        content = sorted(content.items())

        return content, True


class CondaPackageIndex(Index):
    """A custom index that creates an package matrix."""

    name = "packages"
    localname = "Package Index"
    shortname = "packages"

    def generate(self, docnames=None):
        content = defaultdict(list)

        environments = {
            name: (dispname, typ, docname, anchor)
            for name, dispname, typ, docname, anchor, _ in self.domain.get_objects()
        }
        environment_packages: Dict[str, Dict[str, CondaPackage]] = self.domain.data[
            "environment_packages"
        ]
        package_environments = defaultdict(list)

        # flip from environment_packages to package_environments
        for environment_name, packages in environment_packages.items():
            for package in packages:
                package_environments[package].append(environment_name)

        # convert the mapping of package to environments to produce the expected
        # output, shown below, using the package name as a key to group
        #
        # name, subtype, docname, anchor, extra, qualifier, description
        for package, environment_names in package_environments.items():
            for environment_name in environment_names:
                dispname, typ, docname, anchor = environments[environment_name]
                content[package].append(
                    (
                        dispname,
                        0,
                        docname,
                        anchor,
                        typ,
                        "",
                        environment_packages[environment_name][package].version,
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
        "package": CondaPackageDirective,
    }
    indices = {CondaEnvironmentIndex, CondaPackageIndex}
    initial_data = {"environments": [], "environment_packages": {}}
    object_types: Dict[str, ObjType] = {
        "environment": ObjType("environment", "environment", "obj")
    }

    def get_objects(self):
        for obj in self.data["environments"]:
            yield (obj)

    def add_environment(self, sig: str, packages: List[CondaPackage]):
        name = "{}.{}".format("environment", sig)
        anchor = "environment-{}".format(sig)

        self.data["environment_packages"][name] = {pkg.name: pkg for pkg in packages}
        # name, dispname, type, docname, anchor, priority
        self.data["environments"].append(
            (name, sig, "Environment", self.env.docname, anchor, 0)
        )


def obj_transform(app, domain, objtype, contentnode):
    # contentnode += nodes.list_item("hello!")
    # print("obj_transform", app, domain, objtype, contentnode)
    pass


def setup(app: Sphinx):
    app.add_domain(CondaDomain)
    app.connect("html-collect-pages", collect_pages)
    app.connect("object-description-transform", obj_transform)

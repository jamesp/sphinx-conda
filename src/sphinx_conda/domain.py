from collections import defaultdict
from typing import Dict, Iterator, List, cast

from sphinx.roles import XRefRole
from .directives import PackageListDirective, CondaEnvironmentDirective

from .util import object_desc
from .model import CondaLockfile, CondaPackage, CondaYamlfile, Environment
from sphinx.domains import Domain, Index, ObjType


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

        # the yaml file provides explicit packages, which will be
        # set to explicit = True below
        # so if a yaml file is provided, set all lockfile to
        # explicit=False (i.e. implicit dependencies)
        # if no yamlfile is provided, set explicit=None (i.e. unknown)
        lockfile_explicit = False if env.yamlfile else None
        if env.lockfile:
            lock_obj = CondaLockfile.load(env.lockfile)
            for pkg in lock_obj.packages:
                pkg.explicit = lockfile_explicit
                packages[pkg.name] = pkg
        if env.yamlfile:
            yaml_obj = CondaYamlfile.load(env.yamlfile)
            for pkg in yaml_obj.dependencies:
                if pkg.name not in packages:
                    packages[pkg.name] = pkg
                packages[pkg.name].explicit = True

        self.data["environment_packages"][idx] = list(packages.values())
        obj = object_desc(idx, env.name, "Environment", docname, anchor, 0)
        self.data["environment_refs"].append(obj)
        self.data["environments"][idx] = env

    def get_environment_packages(self, idx: str) -> List[CondaPackage]:
        return self.data["environment_packages"][idx]

    def get_environment(self, idx: str) -> Environment:
        return self.data["environments"][idx]

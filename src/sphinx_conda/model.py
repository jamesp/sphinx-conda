from functools import total_ordering
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

import yaml
from pydantic import BaseModel

from .util import split


@total_ordering
class CondaPackage(BaseModel):
    name: str
    version: Optional[str]
    build: Optional[str]
    url: Optional[str]
    md5: Optional[str]
    # whether the package is named in the conda environment.yml
    explicit: Optional[bool] = None

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

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, CondaPackage):
            return self.name < other.name
        else:
            return NotImplemented


class CondaYamlfile(BaseModel):
    name: str
    dependencies: List[CondaPackage]
    filename: Path

    @classmethod
    def load(cls, filename: Union[str, Path]) -> "CondaYamlfile":
        filename = Path(filename)
        if not filename.exists():
            raise FileNotFoundError(f"Environment file {filename} doesn't exist")
        with open(filename, "r") as fh:
            raw = yaml.safe_load(fh)
            if raw.get("dependencies"):
                deps = []
                for d in raw["dependencies"]:
                    name, ver = split(d, "=", 1)
                    deps.append({"name": name, "version": ver, "explicit": True})
                raw["dependencies"] = deps
            obj = CondaYamlfile(filename=filename, **raw)
        return obj


class CondaLockfile(BaseModel):
    packages: List[CondaPackage]
    filename: Path

    @classmethod
    def load(cls, filename: Union[str, Path]) -> "CondaLockfile":
        filename = Path(filename)
        if not filename.exists():
            raise FileNotFoundError(f"Environment lockfile {filename} doesn't exist")
        with open(filename, "r") as fh:
            pkgs: List[CondaPackage] = []
            for line in fh:
                line = line.strip()
                if line.startswith("#"):
                    continue
                if line.upper() == "@EXPLICIT":
                    continue
                pkgs.append(CondaPackage.from_url(line))
        return CondaLockfile(filename=filename, packages=pkgs)


# class Environment(BaseModel):
#     name: str
#     yamlfile: Optional[CondaYamlfile] = None
#     lockfile: Optional[CondaLockfile] = None


class Environment(BaseModel):
    name: str
    yamlfile: Optional[Path] = None
    lockfile: Optional[Path] = None

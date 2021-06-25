from pathlib import Path
from typing import Any, Dict, Generator, TYPE_CHECKING, Tuple, cast

import docutils.parsers.rst.directives as directives
from docutils import nodes
from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.directives import ObjectDescription
from sphinx.ext.viewcode import is_supported_builder, viewcode_anchor
from sphinx.util import status_iterator

if TYPE_CHECKING:
    from sphinx_conda.domain import CondaDomain

from ..model import Environment


OUTPUT_DIR = Path("_environments")


class CondaEnvironmentDirective(ObjectDescription[Environment]):
    required_arguments = 1
    final_argument_whitespace = True
    has_content = True
    objtype = "environment"
    option_spec = {
        "yamlfile": directives.path,
        "lockfile": directives.path,
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

        yamlfile = None
        if "yamlfile" in self.options:
            yamlfile = self.rel_path(Path(self.options.get("yamlfile")))

        lockfile = None
        if "lockfile" in self.options:
            lockfile = self.rel_path(Path(self.options.get("lockfile")))

        environment = Environment(
            name=sig,
            yamlfile=yamlfile,
            lockfile=lockfile,
        )
        return environment

    def add_target_and_index(
        self, name: Environment, sig: str, signode: addnodes.desc_signature
    ):
        # the super method has signature (name, sig, signode)
        # but really we know name to be an environment obj
        signode["ids"].append("environment" + "-" + sig)
        signode["_conda_yamlfile"] = str(name.yamlfile)
        signode["_conda_lockfile"] = str(name.lockfile)
        domain = cast("CondaDomain", self.env.get_domain("conda"))
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

    domain = cast("CondaDomain", env.get_domain("conda"))
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

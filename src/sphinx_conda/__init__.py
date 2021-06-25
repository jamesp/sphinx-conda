__version__ = "0.1.0"

from sphinx_conda.directives.environment import (
    collect_pages as environment_collect_pages,
)
from .domain import CondaDomain

from sphinx.application import Sphinx


def setup(app: Sphinx):
    app.add_domain(CondaDomain)
    app.connect("html-collect-pages", environment_collect_pages)
    # app.connect("object-description-transform", obj_transform)

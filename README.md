# sphinx-conda

This package is a plugin to [Sphinx](https://www.sphinx-doc.org/en/master/index.html)
for documenting conda environments and packages. For an example, see `docs`.

## Installation

Not yet published on pypi, to install direct from github:

`python -m pip install git+https://github.com/jamesp/sphinx-conda`

`sphinx-conda` requires the `sphinx.ext.autoview` plugin to provide links to the
source code. To use, add both to your plugins list in the Sphinx `conf.py`,
making sure that `"sphinx.ext.viewcode"` comes earlier in the list:

```
extensions = [..., "sphinx.ext.viewcode", "sphinx_conda"]
```

## Usage

Conda environments are assumed to be defined by one or both of two files:

1. [An environment yaml file](https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#creating-an-environment-from-an-environment-yml-file).
   This is contains the unresolved list of packages.
2. [A conda lock file](https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#building-identical-conda-environments).
   This specifies the complete list of conda packages that define a resovled environment.
   A conda lockfile can be created either by using `conda list --explicit` when in
   an active conda environment, or by using
   [conda-lock](https://github.com/conda-incubator/conda-lock) to resolve the
   environment yaml file.

`sphinx-conda` provides two directives for including conda environments in
sphinx `.rst` documentation files.

1. `conda:environment <display-name>`. Create an environment documentation entry.
   Arguments:

   - `:yamlfile: <../path/relative/to/doc/environment.yml>`
   - `:lockfile: <../path/relative/to/doc/environment.lock>`

2. `conda:packagelist`. Inside a `conda:environment` directive, this will
   print the list of packages and their versions given in the lockfile and/or
   environment file. Arguments:

   - `:hide-implicit:` Only show the packages explicitly listed in the
     `environment.yml` dependencies list. i.e. do not show any
     dependencies-of-dependencies.
   - `:hide-explicit:` Only show packages that have been brought into the
     environment as dependencies of required packages. Using both of these
     optional arguments is useful if you want to separate implicit and explicit
     dependencies into different sections of your documentation.
   - This directive will also take the same width and alignment options
     as [docutils `list-table`s](https://docutils.sourceforge.io/docs/ref/rst/directives.html#list-table).

See below for an example of using both directives.

```
The development environment can be created using our ``requirements/environment.yml``
file.

.. conda:environment:: dev-environment
   :yamlfile: ../environments/dev-environment.yml
   :lockfile: ../environments/dev-environment-linux-64.lock

   This environment provides all the packages that we currently build and
   test our software against.

   .. conda:packagelist:: Current tested package list and versions
      :hide-implicit:

   To setup the development environment we recommend using the lockfile which
   will install the exact same versions as above.  To install::

      conda create -n dev-environment --file environments/dev-environment.lock

   The additional following packages are also included in the environment to satisfy
   the dependencies of our dependencies.  If one of these packages below becomes an
   explicit dependency of our project, we should add it to ``dev-environment.yml``
   and ``environment.yml``.

   .. conda:packagelist:: Sub-dependencies
      :hide-explicit:

```

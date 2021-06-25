.. stack documentation master file, created by
   sphinx-quickstart on Sun Jun 20 11:37:58 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to stack's documentation!
=================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
* :ref:`conda-packages`

Title
-----

This is an example of using the ``sphinx-conda`` extension.

.. conda:environment:: dev-environment
   :yamlfile: ../environments/dev-environment.yml
   :lockfile: ../environments/dev-environment-linux-64.lock

   This environment provides all the packages that we currently build and
   test our software against.

   .. conda:packagelist:: Current tested package list and versions
      :align: left
      :width: 100%
      :widths: 3 2 2
      :hide-implicit:

   To setup the development environment we recommend using the lockfile which
   will install the exact same versions as above.  To install::

      conda create -n dev-environment --file environments/dev-environment.lock

   The additional following packages are also included in the environment to satisfy
   the dependencies of our dependencies.  If one of these packages below becomes an
   explicit dependency of our project, we should add it to ``dev-environment.yml``
   and ``environment.yml``.

   .. conda:packagelist:: Sub-dependencies
      :align: left
      :width: 100%
      :widths: 3 2 2
      :hide-explicit:
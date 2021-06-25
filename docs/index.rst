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


Here is an env file with some more details:


.. conda:environment:: basic
   :envfile: ../environments/basic.yml
   :lockfile: ../environments/basic.lock

   Basic information about this environment


.. conda:environment:: test
   :envfile: ../environments/test.yml
   :lockfile: ../environments/test.lock

   Here's a second environment, similar but with different packages.

   .. conda:packagelist:: Packages in the environment
      :align: left
      :width: 100%
      :widths: 3 2 2
      :hide-implicit:


   .. conda:packagelist:: Dependencies required by packages above
      :align: left
      :width: 100%
      :widths: 3 2 2
      :hide-explicit:

   Some more content
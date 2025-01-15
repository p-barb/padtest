.. padtest documentation master file, created by
   sphinx-quickstart on Sat Mar 23 15:25:43 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to padtest's documentation!
===================================

Load test axisymmetric or strip pad foundations subjected to static or
dynamic vertical, horizontal or flexural loads in 
`Plaxis 2D <https://www.bentley.com/software/plaxis-2d/#:~:text=PLAXIS%20is%20a%20computer%20application,code%20of%20the%20software%20application.>`_.


.. toctree::
   :maxdepth: 1
   :caption: Contents:
   
   Installation
   Workflow <workflow.ipynb>
   Geometry <geometry.ipynb>
   Materials <materials.ipynb>
   Foundation tests <test.ipynb>
   Changelog

Plaxis version
--------------

Current padtest version (1.0.4) works with Plaxis version 2024.1. Plaxis
scripting commands are updated between verions, making the current
release of padtest incompatible with them. Previous releases were
programed for:

 - Plaxis 2023.2 - padtest 1.0.1
 - Plaxis 2024.1 - padtest 1.0.2
 - Plaxis 2024.1 - padtest 1.0.3
 - Plaxis 2024.1 - padtest 1.0.4

Acknowledgment
--------------

:code:`padtest` is developed by Pablo Barbieri (pbarbie2@uwo.ca). Please, cite this repository as: 

*Barbieri, P. (2025). padtest (Version 1.0.4) [Computer software]. https://github.com/p-barb/padtest*


License
-------
Distributed under the MIT License.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

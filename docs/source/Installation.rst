Installation
============

Requirements
------------

``padtest`` can either be used within the `Plaxis remote scripting Python wrap <https://communities.bentley.com/products/geotech-analysis/w/wiki/46005/using-plaxis-remote-scripting-with-the-python-wrapper>`_ 
or in a regular Python environment. ``padtest`` requires `pandas <https://pandas.pydata.org/docs/index.html>`_
which is not included by default in Plaxis' Python environment. To 
install it, or any other package, follow the instructions listed on
`Plaxis site <https://communities.bentley.com/products/geotech-analysis/w/wiki/51822/how-to-install-additional-python-modules-in-plaxis>`_.

To use ``padtest`` in a custom Python environment, the 
``plxscripting`` package must be installed in that environment along 
all other required packages. ``plxscripting`` cannot be installed
using conda or pip. Instead, it must be installed following 
`these instructions <https://communities.bentley.com/products/geotech-analysis/w/wiki/51822/how-to-install-additional-python-modules-in-plaxis>`_.

.. warning::
    ``plxscripting`` requires Python 3.7. **It will crash with later versions.**

Installation
------------

.. code-block:: python

    pip install padtest

Clone the repo
--------------

.. code-block:: python

    git clone https://github.com/p-barb/padtest



Library API
===========

Core library functionality.

The ``st2.api`` module is the recommended public API. It re-exports all
functions from ``st2.lib`` and adds step functions for training workflows.

Public API
----------

.. automodule:: st2.api
   :members:
   :undoc-members:
   :show-inheritance:

Project Setup
-------------

.. automodule:: st2.lib.setup
   :members:
   :undoc-members:

Project Validation
------------------

.. automodule:: st2.lib.validate
   :members:
   :undoc-members:

Configuration
-------------

.. automodule:: st2.lib.config
   :members:
   :undoc-members:
   :no-index:

Data Structures
---------------

Dictionary
~~~~~~~~~~~

.. automodule:: st2.lib.dictionary
   :members:
   :undoc-members:

Phoneset
~~~~~~~~

.. automodule:: st2.lib.phoneset
   :members:
   :undoc-members:

Transcription
~~~~~~~~~~~~~

.. automodule:: st2.lib.transcription
   :members:
   :undoc-members:

Models
------

.. automodule:: st2.lib.model
   :members:
   :undoc-members:
   :show-inheritance:

Low-level C Bindings
--------------------

For advanced users who need direct access to C functions:

.. automodule:: st2.lib._st2c
   :members:
   :undoc-members:
   :show-inheritance:

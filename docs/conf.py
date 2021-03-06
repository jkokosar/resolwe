# -*- coding: utf-8 -*-

import django
import os

base_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..")

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.settings')

# Manual setup is required for standalone Django usage
django.setup()

# Get package metadata from 'resolwe/__about__.py' file
about = {}
with open(os.path.join(base_dir, 'resolwe', '__about__.py')) as f:
    exec(f.read(), about)

# -- General configuration ------------------------------------------------

# The extension modules to enable.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.coverage',
    'sphinx.ext.viewcode',
]

# The suffix(es) of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'Resolwe'
version = about['__version__']
release = version
author = about['__author__']
copyright = about['__copyright__']

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = None

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build', 'CHANGELOG.rst']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = False

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.
html_theme = 'sphinx_rtd_theme'

# Output file base name for HTML help builder.
htmlhelp_basename = 'Resolwedoc'

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'https://docs.python.org/': None}

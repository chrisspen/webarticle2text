=======================================================================
webarticle2text - Extracts the main article text from a webpage.
=======================================================================

Overview
========

Attempts to locate and extract the largest cluster of text in a
webpage. It does this by walking the DOM-tree, identifying all text
segments and their depth inside the DOM, appends all text at roughly
the same depth, and then returns the chunk with the largest total
length.

This approach usually works well with typical news sites where one
news article is displayed per URL. This approach usually fails with
URLs displaying multiple news blurbs (e.g. news aggregators).

Installation
------------

Install dependencies:

::

    sudo pip install pytidylib
    sudo pip install chardet

Install the package:

::

    python setup.py build
    sudo python setup.py install

Usage
-----

You can invoke the script either as a Python module:

::

    import webarticle2text
    print webarticle2text.extractFromURL("http://some/arbitrary/url")

or as a standalone command line script:

::    

    webarticle2text.py http://some/arbitrary/url
    
Note, to use it from the command line, you'll need to ensure it has execute
permission and is located in your PATH. On most platforms, this should
automatically be done by setup.py.

History
-------

1.0.0 - 2008.9.16
Initial public release.

1.2.0 - 2011.1.3
Update to support Unicode.

1.2.2 - 2011.12.17
Cleaned up installation procedure and documentation and moved to github.com. 

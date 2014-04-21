from distutils.core import setup
import webarticle2text
setup(name='webarticle2text',
    version=webarticle2text.__version__,
    description='Extracts the main article text from a webpage.',
    author='Chris Spencer',
    author_email='chrisspen@gmail.com',
    url='https://github.com/chrisspen/webarticle2text',
    license='LGPL License',
    py_modules=['webarticle2text'],
    scripts=['webarticle2text.py'],
    install_requires=['pytidylib6', 'chardet', 'six'],
    #https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers = [
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.2',
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Text Processing :: General',
    ],
    platforms=['OS Independent'],)

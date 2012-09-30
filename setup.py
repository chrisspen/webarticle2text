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
    install_requires=['pytidylib', 'chardet'],
    classifiers = [
        "Programming Language :: Python",
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: General",
    ],
    platforms=['OS Independent'],)

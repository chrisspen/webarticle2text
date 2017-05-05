#!/usr/bin/env python
"""
File: webarticle2text.py

Copyright (C) 2008 Chris Spencer (chrisspen at gmail dot com)

Attempts to locate and extract the largest cluster of text in a
webpage. It does this by walking the DOM-tree, identifying all text
segments and their depth inside the DOM, appends all text at roughly
the same depth, and then returns the chunk with the largest total
length.

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 3 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
"""
from __future__ import print_function

import os
import sys
import time
import formatter
#import htmlentitydefs
#import htmllib
#import httplib
#import HTMLParser
import mimetypes
import re
#import StringIO
#import urllib2
import hashlib
import requests
#import robotparser

# http://pythonhosted.org/six/
# Note, you may need to install pip for python3 via:
# sudo apt-get install python3-pip
import six
from six.moves import html_entities as htmlentitydefs
from six.moves.html_parser import HTMLParser
from six.moves import http_client as httplib
try:
    from six.moves import cStringIO as StringIO
except ImportError:
    from six import StringIO
from six.moves.urllib import parse as urlparse
from six.moves.urllib.error import HTTPError
from six.moves.urllib.request import OpenerDirector, Request, urlopen
from six.moves.urllib import robotparser

from fake_useragent import UserAgent

ua = UserAgent()

u = six.u
unicode = six.text_type # pylint: disable=redefined-builtin
unichr = six.unichr # pylint: disable=redefined-builtin

def get_unicode(text):
    try:
        text = unicode(text, 'utf-8')
    except TypeError:
        return text

def unescapeHTMLEntities(text):
   """Removes HTML or XML character references
      and entities from a text string.
      keep &amp;, &gt;, &lt; in the source code.
   from Fredrik Lundh
   http://effbot.org/zone/re-sub.htm#unescape-html
   """
   def fixup(m):
      text = m.group(0)
      if text[:2] == "&#":
         # character reference
         try:
            if text[:3] == "&#x":
               return unichr(int(text[3:-1], 16))
            else:
               return unichr(int(text[2:-1]))
         except ValueError:
            pass
      else:
         # named entity
         try:
            text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
         except KeyError:
            pass
      return text # leave as is
   return re.sub("&#?\w+;", fixup, text)

IGNORED_TAGS = (
    'script', 'style', 'option', 'ul', 'li', 'legend', 'object', 'noscript',
    'label', 'footer', 'nav', 'aside',
)

class TextExtractor(HTMLParser):
    """
    Attempts to extract the main body of text from an HTML document.

    This is a messy task, and certain assumptions about the story text
    must be made:

    The story text:
    1. Is the largest block of text in the document.
    2. Sections all exist at the same relative depth.
    """

    dom = []
    path = [0]

    def __init__(self):
        HTMLParser.__init__(self)
        self._ignore = False
        self._ignorePath = None
        self._lasttag = None
        self._depth = 0
        self.depthText = {} # path:text
        self.counting = 0
        self.lastN = 0
        self.pathBlur = 5

    def handle_starttag(self, tag, attrs):
        ignore0 = self._ignore
        tag = tag.lower()
        if tag in IGNORED_TAGS:
            self._ignore = True
        attrd = dict(attrs)
        self._lasttag = tag.lower()
        self._depth += 1
        self.path += [self.lastN]
        self.lastN = 0

        # Ignore footer garbage.
        if 'id' in attrd and 'footer' in attrd['id'].lower():
            self._ignore = True
        elif 'id' in attrd and 'copyright' in attrd['id'].lower():
            self._ignore = True
        elif 'class' in attrd and 'footer' in attrd['class'].lower():
            self.counting = max(self.counting, 1)
            self._ignore = True
        elif 'class' in attrd and 'copyright' in attrd['class'].lower():
            self._ignore = True

        # If we just started ignoring, then remember the initial path
        # so we can later know when to start un-ignoring again.
        if self._ignore and not ignore0:
            self._ignorePath = tuple(self.path)

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if self._ignore and tuple(self.path) == self._ignorePath:
            self._ignore = False

        self._depth -= 1
        if len(self.path):
            self.lastN = self.path.pop()
        else:
            self.lastN = 0
        self.lastN += 1

    def handle_data(self, data, entity=False):
        if len(data) > 0 and not self._ignore:

            # Skip blocks of text beginning with 'copyright', which usually
            # indicates a copyright notice.
            _data = data.strip().lower()
            if _data.startswith('copyright') and not self._ignore:
                self._ignore = True
                self._ignorePath = tuple(self.path)
                return

            if data:

                rpath = tuple(self.path[:-self.pathBlur])
                self.depthText.setdefault(rpath, [])
                self.depthText[rpath] += [data]

                # Allow one more layer below, to include
                # text inside <i></i> or <b></b> tags.
                # Unfortuantely, this will include a lot of crap
                # in the page's header and footer, so we'll
                # prefix this text with '#' and strip these out later.
                rpath2 = tuple(self.path[:-self.pathBlur-1])
                self.depthText.setdefault(rpath2, [])
                self.depthText[rpath2] += ['#'+data]

    def handle_charref(self, name):
        if name.isdigit():
            text = unescapeHTMLEntities(get_unicode('&#'+name+';'))
        else:
            text = unescapeHTMLEntities(get_unicode('&'+name+';'))
        self.handle_data(text, entity=True)

    def handle_entityref(self, name):
        self.handle_charref(name)

    def get_plaintext(self):
        maxLen, maxPath, maxText, maxTextList = 0, (), '', []
        for path, textList in six.iteritems(self.depthText):

            # Strip off header segments, prefixed with a '#'.
            start = True
            text = []
            for t in textList:
                if len(t.strip()):
                    if t.startswith('#') and start:
                        continue
                    start = False
                text.append(t)

            # Strip off footer segments, prefixed with a '#'.
            start = True
            textList = reversed(text)
            text = []
            for t in textList:
                if len(t.strip()):
                    if t.startswith('#') and start:
                        continue
                    start = False
                text.append(t)
            text = reversed(text)

            text = u('').join(text).replace('#', '')
            text = text.replace(u('\xa0'), ' ')
            text = text.replace(u('\u2019'), "'")
            # Compress whitespace.
            text = re.sub("[\\n\\s]+", u(' '), text).strip()
#            print('old:',(maxLen,maxPath,maxText,maxTextList))
#            print('new:',(len(text),path,text,textList))
            maxLen, maxPath, maxText, maxTextList = max(
                (maxLen, maxPath, maxText, maxTextList),
                (len(text), path, text, textList),
            )

        return maxText

    def parse_endtag(self, i):
        # This is necessary because the underlying HTMLParser is buggy and
        # unreliable.
        try:
            return HTMLParser.parse_endtag(self, i)
        except AttributeError:
            return -1

    def error(self, msg):
        # ignore all errors
        pass

#class HTMLParserNoFootNote(htmllib.HTMLParser):
class HTMLParserNoFootNote(HTMLParser):
    """
    Ignores link footnotes, image tags, and other useless things.
    """

    anchor = None

    textPattern = None

    path = [0]

    def handle_starttag(self, tag, attrs, *args):
        time.sleep(0.5)
        self.path += [0]
        if tag == 'script':
            pass

    def handle_endtag(self, tag, *args):
        self.path.pop()
        self.path[-1] += 1
        if tag == 'script':
            pass

    def anchor_end(self):
        if self.anchor:
            #self.handle_data("[%d]" % len(self.anchorlist))
            self.anchor = None

    def handle_image(self, src, alt, *args):
        pass

    def handle_data(self, data):
        if self.textPattern:
            data = ' '.join(self.textPattern.findall(data))
        #htmllib.HTMLParser.handle_data(self, data)
        HTMLParser.handle_data(self, data)

def extractFromHTML(html, blur=5):
    """
    Extracts text from HTML content.
    """

    #html = html.encode('utf-8', errors='ignore')
    try:
        html = unicode(html, errors='ignore')
    except TypeError:
        pass
    assert isinstance(html, unicode)

    # Create memory file.
    _file = StringIO()

    # Convert html to text.
    f = formatter.AbstractFormatter(formatter.DumbWriter(_file))
    p = TextExtractor()
    p.pathBlur = blur
    p.feed(html)
    p.close()
    text = p.get_plaintext()

    # Remove stand-alone punctuation.
    text = re.sub("\s[\(\),;\.\?\!](?=\s)", " ", text).strip()

    # Compress whitespace.
    text = re.sub("[\n\s]+", " ", text).strip()

    # Remove consequetive dashes.
    text = re.sub("\-{2,}", "", text).strip()

    # Remove consequetive periods.
    text = re.sub("\.{2,}", "", text).strip()

    return text

def tidyHTML(dirtyHTML):
    """
    Runs an arbitrary HTML string through Tidy.
    """
    try:
        from tidylib import tidy_document
    except ImportError as e:
        raise ImportError(("%s\nYou need to install pytidylib.\n" +
             "e.g. sudo pip install pytidylib") % e)
    options = {
        'output-xhtml':1,
        #add_xml_decl=1,#option in tidy but not pytidylib
        'indent':1,
        'tidy-mark':1,
        #'char-encoding':'utf8',
        'char-encoding':'raw',
    }
    html, errors = tidy_document(dirtyHTML, options=options)
    return html

def generate_key(s, pattern="%s.txt"):
    """
    Generates the cache key for the given string using the content in pattern
    to format the output string
    """
    h = hashlib.sha1()
    #h.update(s)
    h.update(s.encode('utf-8'))
    return pattern % h.hexdigest()

def cache_get(cache_dir, cache_key, default=None):
    """
    Returns the content of a cache item or the given default
    """
    filename = os.path.join(cache_dir, cache_key)

    if os.path.isfile(filename):
        with open(filename, 'r') as f:
            return f.read()

    return default

def cache_set(cache_dir, cache_key, content):
    """
    Creates a new cache file in the cache directory
    """
    filename = os.path.join(cache_dir, cache_key)

    with open(filename, 'w') as f:
        f.write(content)

def cache_info(cache_dir, cache_key):
    """
    Returns the cache files mtime or 0 if it does not exists
    """
    filename = os.path.join(cache_dir, cache_key)
    return os.path.getmtime(filename) if os.path.exists(filename) else 0

def fetch(url, timeout=5, userAgent=None, only_mime_types=None):
    """
    Retrieves the raw content of the URL.
    """
    headers = {}
    if userAgent:
        headers['User-agent'] = str(userAgent)
    else:
        headers['User-agent'] = ua.random

    #request = Request(url=url, headers=headers)
    #response = urlopen(request, timeout=timeout)
    response = requests.get(url, headers=headers, timeout=timeout)

    # Return nothing of the content isn't one of the target mime-types.
    if only_mime_types:
        assert isinstance(only_mime_types, (tuple, list))
        # Check for mimetype by looking at pattern in the URL.
        # Not super accurate, but very fast.
        ct, mt_encoding = mimetypes.guess_type(url)
        # Then check for mimetype by actually requesting the resource and
        # looking at the response.
        # More accurate, but slower since we actually have to send a request.
        if not ct:
            response_info = response.info()
            ct = (response_info.getheader('Content-Type') or '').split(';')[0]
        #TODO:if still undefined, use magic.Magic(mime=True).from_file(url)?
        if ct not in only_mime_types:
            return
    try:
        #return response.read()
        return response.text
    except httplib.IncompleteRead as e:
        # This should rarely happen, and is often the fault of the server
        # sending a malformed response.
        #TODO:just abandon all content and return '' instead?
        return e.partial

def check_robotstxt(url, useCache, cache_dir, userAgent=None):
    scheme, netloc, url_path, query, fragment = urlparse.urlsplit(url)
    robotstxt_url = urlparse.urlunsplit((
        scheme,
        netloc,
        '/robots.txt',
        '',
        '',
    ))

    key = generate_key(robotstxt_url)

    robots_parser = robotparser.RobotFileParser()
    cached_content = cache_get(cache_dir, key) if useCache else ''
    threshold = (time.time() - 86400 * 7)

    if not cached_content or cache_info(cache_dir, key) < threshold:
        try:
            cached_content = fetch(robotstxt_url, userAgent=userAgent)
            if useCache:
                cache_set(cache_dir, key, cached_content)
        except HTTPError as he:
            # this block mimics the behaviour in the robotparser.read() method
            if he.code in (401, 403):
                robots_parser.disallow_all = True
            elif he.code >= 400:
                robots_parser.allow_all = True
            else:
                raise he
            cached_content = ''

    try:
        cached_content = str(cached_content, encoding='utf8')
    except TypeError:
        pass
    robots_parser.parse((x for x in cached_content.split('\n')))
    default_useragent = None
    for k, v in OpenerDirector().addheaders:
        if k == "User-agent":
            default_useragent = v
            break

    return robots_parser.can_fetch(userAgent or default_useragent, url)

def extractFromURL(url,
    cache=False,
    cacheDir='_cache',
    verbose=False,
    encoding=None,
    filters=None,
    userAgent=None,
    timeout=5,
    blur=5,
    ignore_robotstxt=False,
    only_mime_types=None,
    raw=False):
    """
    Extracts text from a URL.

    Parameters:
    url := string
        Remote URL or local filename where HTML will be read.
    cache := bool
        True=store and retrieve url from cache
        False=always retrieve url from the web
    cacheDir := str
        Directory where cached url contents will be stored.
    verbose := bool
        True=print logging messages
        False=print no output
    encoding := string
        The encoding of the page contents.
        If none given, it will attempt to guess the encoding.
        See http://docs.python.org/howto/unicode.html for further info
        on Python Unicode and encoding support.
    filters := string
        Comma-delimited list of filters to apply before parsing.
    only_mime_types := list of strings
        A list of mime-types to limit parsing to.
        If the mime-type of the raw-content retrieved does not match
        one of these, a value of None will be returned.
    """

    blur = int(blur)

    try:
        import chardet
    except ImportError as e:
        raise ImportError(("%s\nYou need to install chardet.\n" + \
             "e.g. sudo pip install chardet") % e)

    if only_mime_types and isinstance(only_mime_types, six.text_type):
        only_mime_types = only_mime_types.split(',')

    # Load url from cache if enabled.
    if cache:
        if not os.path.isdir(cacheDir):
            cache_perms = 488 # 750 in octal, '-rwxr-x---'
            os.makedirs(cacheDir, cache_perms)

        cache_key = generate_key(url)
        cached_content = cache_get(cacheDir, cache_key)
        if cached_content:
            return cached_content

    if not ignore_robotstxt:
        if not check_robotstxt(url, cache, cacheDir, userAgent=userAgent):
            if verbose: print("Request denied by robots.txt")
            return ''

    # Otherwise download the url.
    if verbose: print('Reading %s...' % url)
    html = fetch(
        url,
        timeout=timeout,
        userAgent=userAgent,
        only_mime_types=only_mime_types)
    if not html:
        return ''

    # If no encoding guess given, then attempt to determine
    # encoding automatically.
    if not encoding:
        if isinstance(html, unicode):
            html = html.encode('utf8', 'replace')
        encoding_opinion = chardet.detect(html)
        encoding = encoding_opinion['encoding']
        if verbose: print('Using encoding %s.' % encoding)

    # Save raw contents to cache if enabled.
    if verbose: print('Read %i characters.' % len(html))
    if cache:
        raw_key = generate_key(url, "%s.raw")
        cache_set(cacheDir, raw_key, html)

    # Apply filters.
    if filters:
        filter_names = map(str.strip, filters.split(','))
        for filter_name in filter_names:
            fltr = get_filter(filter_name)
            html = fltr(html)

    # Clean up HTML.
    html = tidyHTML(html)
    if verbose: print('Extracted %i characters.' % len(html))

    # Convert to Unicode.
    if not html:
        return ''
    html = unicode(html, encoding=encoding, errors='replace')
    if raw:
        return html

    # Extract text from HTML.
    res = extractFromHTML(html, blur=blur)
    assert isinstance(res, unicode)

    # Save extracted text to cache if enabled.
    res = res.encode(encoding, 'ignore')
    if cache:
        cache_set(cacheDir, cache_key, res)

    return res

def filter_remove_entities(text):
    return re.sub("&#[a-zA-Z]+", '', text)

def get_filter_names():
    return [
        k.replace('filter_', '')
        for k, v in six.iteritems(globals())
        if k.startswith('filter_')
    ]

def get_filter(name):
    return globals()['filter_' + re.sub('[^a-zA-Z_]', '', name)]

if __name__ == '__main__':
    from optparse import OptionParser
    usage = "usage: %prog [options] <remote url or local filename>"
    parser = OptionParser(usage=usage)
    parser.add_option(
        "-e", "--encoding", dest="encoding",
        default=None,
        help='Manually specifies the encoding to use when '
            'interpreting the url.')
    parser.add_option(
        "-c", "--cache", dest="cache",
        action='store_true',
        default=False,
        help="Stores and loads data from cache.")
    parser.add_option(
        "-d", "--cacheDir", dest="cacheDir",
        default='_cache',
        help="The directory where cache files will be stored.")
    parser.add_option(
        "-u", "--userAgent", dest="userAgent",
        default=None,
        help="The user-agent to use when requesting URLs.")
    parser.add_option(
        "-f", "--filters", dest="filters",
        default=None,
        choices=get_filter_names(),
        help=('A comma-delimited list of pre-processing filters '
            'to apply, one of [%s].') % '|'.join(get_filter_names()))
    parser.add_option(
        "-v", "--verbose", dest="verbose",
        action='store_true',
        default=False,
        help="Displays status messages.")
    parser.add_option(
        '-i', '--ignore-robotstxt', dest="ignore_robotstxt",
        default=False, action="store_true",
        help="Ignore robots.txt when fetching the content.")
    parser.add_option(
        '-m', '--only-mime-types', dest="only_mime_types",
        default=None,
        help="A comma-delimited list of mime-types to limit retrieval to.")
    parser.add_option(
        "-b", "--blur", dest="blur",
        default=5,
        help="The number of DOM levels to include together when searching "
            "for the largest single chunk of text. "
            "A bigger number will find more text, but that text will morel likely be junk. "
            "A smaller number will find less text, but that text is less likely to be junk.")

    (options, args) = parser.parse_args()

    if len(args) < 1:
        parser.print_help()
        sys.exit()

    url = args[0]
    s = extractFromURL(url=url, **options.__dict__)
    s = s.decode('utf-8')
    try:
        sys.stdout.write(s.encode('utf-8', errors='ignore'))
    except TypeError:
        sys.stdout.write(s)
    sys.stdout.write('\n')

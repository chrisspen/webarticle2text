#!/usr/bin/python
"""
File: html2text.py

Copyright (C) 2008  Chris Spencer (chrisspen at gmail dot com)

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
VERSION = (1, 2, 3)
__version__ = '.'.join(map(str, VERSION))
import os, sys, htmllib, formatter, StringIO, re, urllib, HTMLParser, time, htmlentitydefs
try:
    from tidylib import tidy_document
except ImportError, e:
    raise ImportError, "%s\nYou need to install pytidylib.\ne.g. sudo pip install pytidylib" % e
try:
    import chardet
except ImportError, e:
    raise ImportError, "%s\nYou need to install chardet.\ne.g. sudo pip install chardet" % e

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

class TextExtractor(HTMLParser.HTMLParser):
    """
    Attempts to extract the main body of text from an HTML document.
    
    This is a messy task, and certain assumptions about the story text must be made:
    
    The story text:
    1. Is the largest block of text in the document.
    2. Sections all exist at the same relative depth.
    """
    
    dom = []
    path = [0]
    pathBlur = 5
    
    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self._ignore = False
        self._ignorePath = None
        self._lasttag = None
        self._depth = 0
        self.depthText = {} # path:text
        self.counting = 0
        self.lastN = 0
        
    def handle_starttag(self, tag, attrs): 
        ignore0 = self._ignore
        tag = tag.lower()
        if tag in ('script','style','option','ul','li','legend','object','noscript','label'): # 'h1','h2','h3','h4','h5','h6',
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
            self.counting = max(self.counting,1)
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
            if data.strip().lower().startswith('copyright') and not self._ignore:
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
            text = unescapeHTMLEntities(u'&#'+name+';')
        else:
            text = unescapeHTMLEntities(u'&'+name+';')
        self.handle_data(text, entity=True)
                
    def handle_entityref(self, name):
        self.handle_charref(name)
        
    def get_plaintext(self):
        maxLen,maxPath,maxText,maxTextList = 0,None,'',[]
        for path,textList in self.depthText.iteritems():
            
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
                
            text = u''.join(text).replace('#','')
            text = text.replace(u'\xa0',' ')
            text = text.replace(u'\u2019',"'")
            text = re.sub("[\\n\\s]+", u" ", text).strip() # Compress whitespace.
            maxLen,maxPath,maxText,maxTextList = max((maxLen,maxPath,maxText,maxTextList), (len(text),path,text,textList))
        
        return maxText
    
    def parse_endtag(self, i):
        # This is necessary because the underlying HTMLParser is buggy and
        # unreliable.
        try:
            return HTMLParser.HTMLParser.parse_endtag(self, i)
        except AttributeError, e:
            return -1
    
    def error(self,msg):
        # ignore all errors
        pass

class HTMLParserNoFootNote(htmllib.HTMLParser):
    """
    Ignores link footnotes, image tags, and other useless things.
    """
    
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
        htmllib.HTMLParser.handle_data(self, data)
    
def extractFromHTML(html):
    """
    Extracts text from HTML content.
    """
    html = unicode(html)
    assert isinstance(html, unicode)
    
    # Create memory file.
    file = StringIO.StringIO()
    
    # Convert html to text.
    f = formatter.AbstractFormatter(formatter.DumbWriter(file))
    p = TextExtractor()
    p.feed(html)
    p.close()
    text = p.get_plaintext()
    
    # Remove common junk patterns.
    text = re.sub("\s[\(\),;\.\?\!](?=\s)", " ", text).strip() # Remove stand-alone punctuation.
    text = re.sub("[\n\s]+", " ", text).strip() # Compress whitespace.
    text = re.sub("\-{2,}", "", text).strip() # Remove consequetive dashes.
    text = re.sub("\.{2,}", "", text).strip() # Remove consequetive periods.
    
    return text

def tidyHTML(dirtyHTML):
    """
    Runs an arbitrary HTML string through Tidy.
    """
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

def extractFromURL(url, cache=False, cacheDir='_cache', verbose=False, encoding=None, filters=None):
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
        See http://docs.python.org/howto/unicode.html for further info on Python Unicode and encoding support.
    filters := string
        Comma-delimited list of filters to apply before parsing.
    """

    # Load url from cache if enabled.
    if cache:
        if not os.path.isdir(cacheDir):
            os.makedirs(cacheDir)
        fn = os.path.join(cacheDir, re.sub('[^a-zA-Z0-9\-_]+', '', url)+'.txt')
        if os.path.isfile(fn):
            return open(fn).read()

    # Otherwise download the url.
    if verbose: print 'Reading %s...' % url
    html = urllib.urlopen(url).read()

    # If no encoding guess given, then attempt to determine encoding automatically.
    if not encoding:
        encoding_opinion = chardet.detect(html)
        encoding = encoding_opinion['encoding']
        if verbose: print 'Using encoding %s.' % encoding

    # Save raw contents to cache if enabled.
    if verbose: print 'Read %i characters.' % len(html)
    if cache:
        fout = open(fn+'.raw', 'w')
        fout.write(html)

    # Apply filters.
    if filters:
        filter_names = map(str.strip, filters.split(','))
        for filter_name in filter_names:
            filter = get_filter(filter_name)
            html = filter(html)

    # Clean up HTML.
    html = tidyHTML(html)
    if verbose: print 'Extracted %i characters.' % len(html)
    
    # Convert to Unicode.
    html = unicode(html,encoding=encoding,errors='replace')
    
    # Extract text from HTML.
    res = extractFromHTML(html)
    assert isinstance(res, unicode)

    # Save extracted text to cache if enabled.
    res = res.encode(encoding, 'ignore')
    if cache:
        fout = open(fn, 'w')
        fout.write(res)
    return res

def filter_remove_entities(text):
    return re.sub("&#[a-zA-Z]+", '', text)

def get_filter_names():
    return [k.replace('filter_','') for k,v in globals().iteritems() if k.startswith('filter_')]

def get_filter(name):
    return eval('filter_' + re.sub('[^a-zA-Z_]','',name))

if __name__ == '__main__':
    from optparse import OptionParser
    usage = "usage: %prog [options] <remote url or local filename>"
    parser = OptionParser(usage=usage)
    parser.add_option("-e", "--encoding", dest="encoding",
                      default=None,
                      help="manually specifies the encoding to use when interpreting the url")
    parser.add_option("-c", "--cache", dest="cache",
                      action='store_true',
                      default=False,
                      help="stores and loads data from cache")
    parser.add_option("-d", "--cacheDir", dest="cacheDir",
                      default='_cache',
                      help="the directory where cache files will be stored")
    parser.add_option("-f", "--filters", dest="filters",
                      default=None,
                      choices=get_filter_names(),
                      help="a comma-delimited list of pre-processing filters to apply, one of [%s]" % '|'.join(get_filter_names()))
    parser.add_option("-v", "--verbose", dest="verbose",
                      action='store_true',
                      default=False,
                      help="displays status messages")
    (options, args) = parser.parse_args()

    if len(args) < 1:
        parser.print_help()
        sys.exit()

    url = args[0]
    print extractFromURL(url=url, **options.__dict__)

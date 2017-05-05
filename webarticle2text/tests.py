from __future__ import print_function

import os
import sys
import unittest
import codecs
import gc
import re
from collections import defaultdict

from fuzzywuzzy import fuzz
from Levenshtein import distance

from bs4 import BeautifulSoup

import html2text

from readability.readability import Document

from goose import Goose

from newspaper import fulltext

import webarticle2text

FIXTURE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'fixtures'))

# https://github.com/buriy/python-readability
# https://pypi.python.org/pypi/readability-lxml
def get_readability_text(html):
    readable_article = Document(html).summary()
    return readable_article

# https://pypi.python.org/pypi/goose-extractor
# https://pypi.python.org/pypi/goose3/
def get_goose_text(html):
    g = Goose()
    article = g.extract(raw_html=html)
    return article.cleaned_text

def get_beautifulsoup_lxml_text(html):
    soup = BeautifulSoup(html, 'lxml')
    text = soup.get_text()
    return text

def get_beautifulsoup_html5lib_text(html):
    soup = BeautifulSoup(html, 'html5lib')
    text = soup.get_text()
    return text

def get_html2text_text(html):
    return html2text.html2text(html)

def get_newspaper_text(html):
    return fulltext(html)

def mean(seq):
    return sum(seq)/float(len(seq))

class Tests(unittest.TestCase):

    def test_extract(self):
        with open('webarticle2text/fixtures/SAMPLE1.html', 'rb') as fin:
            raw = fin.read()
            ret = webarticle2text.extractFromHTML(raw)
        print(ret)
        self.assertTrue(ret.startswith('Python 3.6.0 is now available!'))
        self.assertTrue(ret.endswith('is now available for download on python.org.'))

    def test_compare(self):
        data = defaultdict(lambda: defaultdict(list)) # {method: {metric: [data]}}
        samples = 5
        methods = [
            ('webarticle2text', webarticle2text.extractFromHTML),
            ('goose', get_goose_text),
            ('readability', get_readability_text),
            ##('beautifulsoup_lxml', get_beautifulsoup_lxml_text),#MemoryError
            ##('beautifulsoup_html5lib', get_beautifulsoup_html5lib_text),#MemoryError
            ('html2text', get_html2text_text),
            ('newspaper', get_newspaper_text),
        ]
        total = len(methods) * samples
        count = 0
        for method, method_func in methods:
            for i in range(1, samples+1):
                count += 1
                print('Processing sample %i with method %s (%i of %i).' % (i, method, count, total))

                raw_fn = os.path.join(FIXTURE_DIR, 'compare/page%i.html' % i)
                expected_fn = os.path.join(FIXTURE_DIR, 'compare/page%i.expected.txt' % i)
                actual_fn = os.path.join(FIXTURE_DIR, 'compare/page%i.%s.actual.txt' % (i, method))

                #raw_text = open().read().encode('utf-8', errors='ignore')
                raw_text = codecs.open(raw_fn, "r", "utf-8", errors='ignore').read()
                #expected_text = open(expected_fn).read().encode('utf-8', errors='ignore')
                expected_text = codecs.open(expected_fn, "r", "utf-8", errors='ignore').read()

                actual_text = method_func(raw_text)
                actual_text = re.sub(r'[\n]+', ' ', actual_text, flags=re.M)
                with open(actual_fn, 'wb')as fout:
                    fout.write(actual_text.encode('utf-8'))

                print('Calculating simple ratio...')
                data[method]['simple_ratios'].append(fuzz.ratio(expected_text, actual_text))

                print('Calculating partial ratio...')
                data[method]['partial_ratios'].append(fuzz.partial_ratio(expected_text, actual_text))

                print('Calculating levenshtein distance...')
                data[method]['levenshtein_distances'].append(distance(expected_text, actual_text))

                gc.collect()

        with open('compare.csv', 'w') as fout:
            print('Method,Mean Simple Ratio,Mean Partial Ratio,Mean Levenshtein Distance', file=fout)
            for method in data:
                row = [
                    method,
                    mean(data[method]['simple_ratios']),
                    mean(data[method]['partial_ratios']),
                    mean(data[method]['levenshtein_distances']),
                ]
                print(','.join(map(str, row)), file=fout)

if __name__ == '__main__':
    unittest.main()

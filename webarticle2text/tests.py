from __future__ import print_function

import unittest

import webarticle2text

class Tests(unittest.TestCase):
    
    def test_extract(self):
        with open('webarticle2text/fixtures/SAMPLE1.html', 'rb') as fin:
            raw = fin.read()
            ret = webarticle2text.extractFromHTML(raw)
        print(ret)
        self.assertTrue(ret.startswith('Python 3.6.0 is now available!'))
        self.assertTrue(ret.endswith('is now available for download on python.org.'))
        
if __name__ == '__main__':
    unittest.main()

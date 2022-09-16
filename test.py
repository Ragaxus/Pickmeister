from bot import Pickmeister
import unittest

class TestPickmeister(unittest.TestCase):

    def test_make_embed_content(self):
        with open('test-input.txt', 'r') as f:
            example_input = f.read()
        print(Pickmeister().make_embed_content(example_input))

if __name__ == '__main__':
    unittest.main()

import unittest
from unittest.mock import patch

import torch

from experiments.full_page_omr.representation.codec_fixtures import fixtures, horn
from experiments.full_page_omr.datasets.clean_page_data import composition_seed, make_score
from experiments.full_page_omr.representation.constrained_decoding import ScoreGrammar, constrained_greedy
from experiments.full_page_omr.representation.score_codec import CodecError, PROFILE, VOCABULARY, W2I, encode


class ConstrainedDecodingTests(unittest.TestCase):
    def replay(self, tokens):
        grammar = ScoreGrammar()
        for index, token in enumerate(tokens):
            self.assertIn(token, grammar.allowed_tokens(), (index, VOCABULARY[token]))
            grammar.consume(token)
        return grammar

    def test_all_fixtures_and_dense_polyphony_are_permitted(self):
        sources = [f.source for f in fixtures()]
        sources += [make_score(composition_seed(71, 'validation', i), kind)
                    for i, kind in enumerate(('horn', 'piano', 'drums'))]
        for source in sources:
            grammar = self.replay(encode(source))
            self.assertTrue(grammar.complete)
            self.assertEqual(grammar.allowed_tokens(), ())
            with self.assertRaises(CodecError):
                grammar.consume(W2I['<eos>'])

    def test_premature_eos_nesting_duplicates_and_required_order(self):
        tokens = encode(horn().source)
        grammar = self.replay(tokens[:tokens.index(W2I['E:pitch']) + 1])
        self.assertNotIn(W2I['<eos>'], grammar.allowed_tokens())
        grammar.consume(W2I['<attrs-end>'])
        self.assertNotIn(W2I['E:note'], grammar.allowed_tokens())
        self.assertNotIn(W2I['<end>'], grammar.allowed_tokens())
        # octave cannot skip required step; step cannot repeat after it closes.
        self.assertNotIn(W2I['E:octave'], grammar.allowed_tokens())
        for word in ('E:step', '<attrs-end>', '<text>', 'V:C', '<value-end>', '<end>'):
            grammar.consume(W2I[word])
        self.assertNotIn(W2I['E:step'], grammar.allowed_tokens())
        self.assertIn(W2I['E:octave'], grammar.allowed_tokens())
        before = grammar.allowed_tokens()
        with self.assertRaises(CodecError):
            grammar.consume(W2I['E:note'])
        self.assertEqual(before, grammar.allowed_tokens())

    def test_enum_values_utf8_and_canonical_literals(self):
        tokens = encode(horn().source)
        index = tokens.index(W2I['E:step'])
        grammar = self.replay(tokens[:index + 1])
        grammar.consume(W2I['<attrs-end>'])
        grammar.consume(W2I['<text>'])
        self.assertNotIn(W2I['V:128'], grammar.allowed_tokens())
        self.assertNotIn(W2I['B:43'], grammar.allowed_tokens())  # C has literal token
        grammar = ScoreGrammar()
        for word in ('<bos>', PROFILE, 'E:score-partwise', 'A:version', 'V:4.0',
                     '<value-end>', '<attrs-end>', 'E:work', '<attrs-end>',
                     'E:work-title', '<attrs-end>', '<text>'):
            grammar.consume(W2I[word])
        self.assertNotIn(W2I['B:ff'], grammar.allowed_tokens())
        self.assertNotIn(W2I['B:00'], grammar.allowed_tokens())
        for byte in 'Māori 🎺'.encode():
            grammar.consume(W2I[f'B:{byte:02x}'])
        self.assertIn(W2I['<value-end>'], grammar.allowed_tokens())
        # An incomplete UTF-8 character cannot terminate a value.
        grammar.consume(W2I['B:c4'])
        self.assertNotIn(W2I['<value-end>'], grammar.allowed_tokens())

    def test_required_attributes_and_sorted_attribute_names(self):
        grammar = self.replay([W2I[w] for w in ('<bos>', PROFILE, 'E:score-partwise')])
        self.assertNotIn(W2I['<attrs-end>'], grammar.allowed_tokens())
        self.assertEqual(grammar.allowed_tokens(), (W2I['A:version'],))
        grammar.consume(W2I['A:version'])
        self.assertEqual(grammar.allowed_tokens(), (W2I['V:4.0'],))

    def test_decoder_masks_bad_logits_preserves_legal_outputs_and_caps(self):
        target = encode(horn().source)
        features = torch.zeros(1)

        class FakeCache:
            def __init__(self, *args):
                pass

            def step(self, token, position):
                logits = torch.full((len(VOCABULARY),), -100.)
                logits[W2I['<pad>']] = 100.
                logits[target[position + 1]] = 50.
                return logits

        with patch('experiments.full_page_omr.training.overfit_pilot.CachedGreedy', FakeCache):
            result = constrained_greedy(None, features, len(target) + 1)
            self.assertEqual(result.tokens, target)
            self.assertTrue(result.grammar_complete)
            self.assertEqual(result.interventions, len(target) - 1)
            capped = constrained_greedy(None, features, 20)
            self.assertEqual(capped.stop_reason, 'token_cap')
            self.assertFalse(capped.grammar_complete)
            self.assertNotEqual(capped.tokens[-1], W2I['<eos>'])

        class LegalCache(FakeCache):
            def step(self, token, position):
                logits = super().step(token, position)
                logits[W2I['<pad>']] = -100.
                return logits

        with patch('experiments.full_page_omr.training.overfit_pilot.CachedGreedy', LegalCache):
            result = constrained_greedy(None, features, len(target))
            self.assertEqual(result.tokens, target)
            self.assertEqual(result.interventions, 0)

    def test_no_finite_continuation_fails_without_repair(self):
        class Cache:
            def __init__(self, *args):
                pass

            def step(self, *args):
                return torch.full((len(VOCABULARY),), -float('inf'))

        with patch('experiments.full_page_omr.training.overfit_pilot.CachedGreedy', Cache):
            result = constrained_greedy(None, torch.zeros(1), 50)
            self.assertEqual(result.stop_reason, 'no_finite_allowed_token')
            self.assertEqual(result.tokens, [W2I['<bos>']])


if __name__ == '__main__':
    unittest.main()

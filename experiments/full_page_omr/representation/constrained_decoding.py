"""Incremental grammar for musvit-score-v1; no targets, renderer or ML required.

Masks illegal token continuations. Grammar completion is not semantic validity:
measure timing, voice overlap, references, spans and canonical divisions still
require the unchanged score codec validator. No repair, backtracking or forced EOS.
"""
import codecs
from dataclasses import dataclass
import math
import re
import xml.etree.ElementTree as ET

from experiments.full_page_omr.representation.score_codec import (ATTRIBUTES, CHILDREN, FREE_TEXT, LITERALS, PROFILE,
                          REPEATABLE, REQUIRED, TEXT, UNORDERED, VOCABULARY, W2I, CodecError)
from experiments.full_page_omr.representation.score_semantics import NOTE_LENGTHS, _fields


BOOL_ATTRS = set('implicit new-system new-page print-object measure use-symbols use-stems filled parentheses line sign cautionary editorial bracket'.split())
TYPE_ATTRS = {tag: {'start', 'stop'} for tag in
              ('tie', 'tied', 'slur', 'tuplet', 'glissando', 'slide', 'dashes', 'pedal')}
TYPE_ATTRS.update(wedge={'crescendo', 'diminuendo', 'stop'}, ending={'start', 'stop', 'discontinue'})
TEXT_ENUMS = {tag: set('CDEFGAB') for tag in ('step', 'root-step', 'bass-step', 'display-step')}
TEXT_ENUMS.update({tag: set(map(str, range(10))) for tag in ('octave', 'display-octave')})
TEXT_ENUMS.update(type=set(NOTE_LENGTHS), notehead={'normal', 'x', 'diamond', 'slash', 'circle-x'},
                  accidental={'sharp', 'flat', 'natural', 'double-sharp', 'flat-flat'},
                  stem={'up', 'down', 'none', 'double'}, sign={'G', 'F', 'C', 'percussion'},
                  beam={'begin', 'continue', 'end', 'forward hook', 'backward hook'})
INTEGER_TEXT = set('octave display-octave alter root-alter bass-alter voice staff staves actual-notes normal-notes diatonic chromatic octave-change clef-octave-change line divisions duration fifths multiple-rest measure-repeat'.split())
REQUIRED_ATTRS = {tag: {'type'} for tag in TYPE_ATTRS}
REQUIRED_ATTRS.update({'score-partwise': {'version'}, 'score-part': {'id'},
                       'part': {'id'}, 'repeat': {'direction'}, 'ending': {'type', 'number'}})


def value_domain(tag, attr):
    if attr is None:
        # Integer spellings such as +01 are legal outside canonical tick values.
        return TEXT_ENUMS.get(tag) if tag not in ('octave', 'display-octave') else None
    if attr in BOOL_ATTRS:
        return {'yes', 'no'}
    if attr == 'placement':
        return {'above', 'below'}
    if attr == 'type':
        return TYPE_ATTRS.get(tag)
    if tag == 'repeat' and attr == 'direction':
        return {'forward', 'backward'}
    if tag == 'score-partwise' and attr == 'version':
        return {'4.0'}
    return None


@dataclass
class Frame:
    node: ET.Element
    phase: str = 'attrs'
    last_attribute: str = ''
    text_seen: bool = False


class ScoreGrammar:
    """Stateful parser; allowed_tokens() is pure, consume() rejects invalid input."""

    def __init__(self):
        self.stage = 'bos'
        self.stack = []
        self.root = None
        self.value_attr = None
        self._allowed = None
        self.value_bytes = b''
        self.value_literal = None

    @property
    def complete(self):
        return self.stage == 'done'

    def _value_valid(self, text):
        frame = self.stack[-1]
        tag, attr = frame.node.tag, self.value_attr
        if not all(c in '\t\n\r' or 0x20 <= ord(c) <= 0xD7FF or
                   0xE000 <= ord(c) <= 0xFFFD or 0x10000 <= ord(c) <= 0x10FFFF for c in text):
            return False
        domain = value_domain(tag, attr)
        if domain is not None and text not in domain:
            return False
        if attr is None:
            if tag not in FREE_TEXT and (not text or text != text.strip()):
                return False
            node = ET.Element(tag, dict(frame.node.attrib))
            node.text = text
            try:
                _fields(node)
            except CodecError:
                return False
        else:
            if attr == 'number' and tag not in ('measure', 'ending'):
                return bool(re.fullmatch(r'[+-]?[0-9]+', text)) and int(text) >= 1
            if attr == 'times':
                return bool(re.fullmatch(r'[+-]?[0-9]+', text)) and int(text) >= 2
            if tag == 'sound' and attr == 'tempo':
                from experiments.full_page_omr.representation.score_semantics import number
                try:
                    number(text, 'tempo', positive=True)
                except CodecError:
                    return False
        return True

    def _byte_prefix_valid(self, data):
        domain = value_domain(self.stack[-1].node.tag, self.value_attr)
        if domain is not None:
            return any(v.encode().startswith(data) and v not in LITERALS for v in domain)
        decoder = codecs.getincrementaldecoder('utf-8')()
        try:
            text = decoder.decode(data, final=False)
        except UnicodeDecodeError:
            return False
        if not all(c in '\t\n\r' or 0x20 <= ord(c) <= 0xD7FF or
                   0xE000 <= ord(c) <= 0xFFFD or 0x10000 <= ord(c) <= 0x10FFFF for c in text):
            return False
        tag, attr = self.stack[-1].node.tag, self.value_attr
        integer = (attr is None and tag in INTEGER_TEXT) or (attr == 'number' and tag not in ('measure', 'ending')) or attr == 'times'
        if integer:
            return bool(re.fullmatch(r'[+-]?[0-9]*', text)) and not decoder.getstate()[0]
        return True

    def _children(self, frame):
        node = frame.node
        allowed = CHILDREN.get(node.tag, '').split()
        seen = [n.tag for n in node]
        for tag in allowed:
            if node.tag not in UNORDERED:
                if tag in seen and tag not in REPEATABLE:
                    continue
                if seen and allowed.index(tag) < allowed.index(seen[-1]):
                    continue
                if any(r not in seen and allowed.index(r) < allowed.index(tag)
                       for r in REQUIRED.get(node.tag, [])):
                    continue
            if node.tag == 'direction-type' and seen and tag != seen[0]:
                continue
            yield W2I['E:' + tag]

    def _can_close(self, frame):
        if frame.node.tag in TEXT and not frame.text_seen:
            # Only fields whose validator accepts absent text may be empty.
            try:
                _fields(frame.node)
            except CodecError:
                return False
        try:
            _fields(frame.node)
        except CodecError:
            return False
        return True

    def allowed_tokens(self):
        if self._allowed is None:
            self._allowed = self._allowed_tokens()
        return self._allowed

    def _allowed_tokens(self):
        fixed = {'bos': '<bos>', 'profile': PROFILE, 'root': 'E:score-partwise', 'eos': '<eos>'}
        if self.stage in fixed:
            return (W2I[fixed[self.stage]],)
        if self.stage == 'done':
            return ()
        if self.stage == 'value':
            if self.value_literal is not None:
                return (W2I['<value-end>'],)
            allowed = []
            if not self.value_bytes:
                allowed.extend(W2I['V:' + v] for v in LITERALS if self._value_valid(v))
            else:
                try:
                    text = self.value_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    text = None
                if text is not None and text not in LITERALS and self._value_valid(text):
                    allowed.append(W2I['<value-end>'])
            # Empty free values are accepted only if the profile permits them.
            if not self.value_bytes and self._value_valid(''):
                allowed.append(W2I['<value-end>'])
            allowed.extend(W2I[f'B:{b:02x}'] for b in range(256)
                           if self._byte_prefix_valid(self.value_bytes + bytes([b])))
            return tuple(sorted(allowed))
        frame = self.stack[-1]
        if frame.phase == 'attrs':
            attrs = ATTRIBUTES.get(frame.node.tag, '').split()
            missing = REQUIRED_ATTRS.get(frame.node.tag, set()) - frame.node.attrib.keys()
            allowed = [W2I['A:' + a] for a in attrs if a > frame.last_attribute and
                       not any(r < a for r in missing)]
            if not missing:
                allowed.append(W2I['<attrs-end>'])
            return tuple(sorted(allowed))
        allowed = list(self._children(frame))
        if frame.node.tag in TEXT and not frame.text_seen and len(frame.node) == 0:
            allowed.append(W2I['<text>'])
        if self._can_close(frame):
            allowed.append(W2I['<end>'])
        return tuple(sorted(allowed))

    def consume(self, token):
        if type(token) is not int or token not in self.allowed_tokens():
            raise CodecError(f'illegal constrained token {token!r} at {self.stage}')
        self._allowed = None
        word = VOCABULARY[token]
        if self.stage in ('bos', 'profile'):
            self.stage = 'profile' if self.stage == 'bos' else 'root'
        elif self.stage == 'eos':
            self.stage = 'done'
        elif self.stage == 'value':
            if word == '<value-end>':
                text = self.value_literal if self.value_literal is not None else self.value_bytes.decode('utf-8')
                if self.value_attr is None:
                    self.stack[-1].node.text = text
                else:
                    self.stack[-1].node.set(self.value_attr, text)
                self.stage = 'element'
            elif word.startswith('V:'):
                self.value_literal = word[2:]
            else:
                self.value_bytes += bytes([int(word[2:], 16)])
        elif word.startswith('E:'):
            node = ET.Element(word[2:])
            if self.stack:
                self.stack[-1].node.append(node)
            else:
                self.root = node
            self.stack.append(Frame(node))
            self.stage = 'element'
        elif word.startswith('A:') or word == '<text>':
            self.value_attr = word[2:] if word.startswith('A:') else None
            if self.value_attr:
                self.stack[-1].last_attribute = self.value_attr
            else:
                self.stack[-1].text_seen = True
            self.value_bytes, self.value_literal = b'', None
            self.stage = 'value'
        elif word == '<attrs-end>':
            self.stack[-1].phase = 'body'
        elif word == '<end>':
            self.stack.pop()
            if not self.stack:
                self.stage = 'eos'


@dataclass
class ConstrainedResult:
    tokens: list[int]
    grammar_complete: bool
    interventions: int
    stop_reason: str


def constrained_greedy(model, features, maxlen):
    """Same cached greedy logits as baseline; only token selection is restricted."""
    import torch
    from experiments.full_page_omr.training.overfit_pilot import CachedGreedy
    if maxlen < 2:
        raise ValueError('maxlen must be at least two')
    grammar = ScoreGrammar()
    tokens = [W2I['<bos>']]
    grammar.consume(tokens[0])
    interventions = 0
    with torch.inference_mode():
        cache = CachedGreedy(model, features)
        for position in range(maxlen - 1):
            logits = cache.step(tokens[-1], position).detach().cpu().tolist()
            allowed = grammar.allowed_tokens()
            candidates = [i for i in allowed if math.isfinite(logits[i])]
            if not candidates:
                return ConstrainedResult(tokens, False, interventions, 'no_finite_allowed_token')
            raw = max(range(len(logits)), key=logits.__getitem__)
            chosen = max(candidates, key=logits.__getitem__)
            interventions += chosen != raw
            grammar.consume(chosen)
            tokens.append(chosen)
            if grammar.complete:
                return ConstrainedResult(tokens, True, interventions, 'eos')
            if features.device.type == 'mps' and (position + 1) % 256 == 0:
                torch.mps.empty_cache()
    return ConstrainedResult(tokens, False, interventions, 'token_cap')

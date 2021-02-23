## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.

"""Generates random "cognates" from two lists of roots

Assumes the output of generate_random_roots_from_lm, which produces a 3-column
output:

root    count     prob
"""

from absl import app
from absl import flags

import collections
import math
import pynini as py
import random
import sys
import time


flags.DEFINE_string("examples", "", "Path to examples")
flags.DEFINE_integer("max_allowed_mappings", 2,
                     "Maximum number of allowed mappings for each phone")
flags.DEFINE_integer("max_zeroes", 1, "Maximum number of insertions/deletions")
flags.DEFINE_bool("initial_only", False,
                  "If true, use only the initial sounds from the pairs, "
                  "per Kessler's approach. Only functional if --use_aligner "
                  "is true")

FLAGS = flags.FLAGS


class Aligner:
  """Class to perform alignments using a constructed FST."""

  def __init__(self):
    self._stats = collections.defaultdict(int)
    self._aligner = py.Fst()
    s = self._aligner.add_state()
    self._aligner.set_start(s)
    self._aligner.set_final(s)

  def compute_alignments(self, pairs, max_zeroes=2,
                         max_allowed_mappings=2,
                         print_mappings=False,
                         initial_only=False):
    """Generalization of Kessler's initials-only match approach.

    Ref: Kessler, Brett. 2001. "The Significance of Word Lists."
    University of Chicago Press.

    Args:
      pairs: list of pairs
      max_allowed_mappings: int, maximum number of mappings allowed
      print_mappings: bool, whether or not to print mappings
      initial_only: bool, if True, only look at the initial segment
    Returns:
      number of matches
    """
    tot = 0
    ins_weight = del_weight = 100
    if initial_only:
      new_pairs = []
      for (p1, p2) in pairs:
        new_pairs.append((p1[:1], p2[:1]))
      pairs = new_pairs
    # Computes initial statistics for any symbol mapping to any symbol assuming
    # no reordering.
    for (p1, p2) in pairs:
      for i in range(len(p1)):
        for j in range(i, len(p2)):
          self._stats[p1[i], p2[j]] += 1
          tot += 1
    if not initial_only:  # If we only consider initials, we don't need 2nd pass
      for (p1, p2) in pairs:
        for i in range(len(p2)):
          for j in range(i, len(p1)):
            self._stats[p1[j], p2[i]] += 1
            tot += 1
    symbols = py.SymbolTable()
    symbols.add_symbol("<epsilon>")
    # Constructs a matcher FST using the initial statistics.
    for (c1, c2) in self._stats:
      label1 = symbols.add_symbol(c1)
      label2 = symbols.add_symbol(c2)
      weight = -math.log(self._stats[c1, c2] / tot)
      self._aligner.add_arc(self._aligner.start(),
                              py.Arc(label1, label2, weight,
                                       self._aligner.start()))
      self._aligner.add_arc(self._aligner.start(),
                              py.Arc(label1, 0, del_weight,
                                       self._aligner.start()))
      self._aligner.add_arc(self._aligner.start(),
                              py.Arc(0, label2, ins_weight,
                                       self._aligner.start()))
    self._aligner.optimize()
    self._aligner.set_input_symbols(symbols)
    self._aligner.set_output_symbols(symbols)
    left_to_right = collections.defaultdict(lambda:
                                              collections.defaultdict(int))
    if not initial_only:
      right_to_left = collections.defaultdict(lambda:
                                                collections.defaultdict(int))
    # Realigns the data using the matcher. NB: we could get fancy and use EM for
    # this...
    for (p1, p2) in pairs:
      f1 = self._make_fst(p1, symbols)
      f2 = self._make_fst(p2, symbols)
      alignment = py.shortestpath(f1 * self._aligner * f2).topsort()
      for s in alignment.states():
        aiter = alignment.arcs(s)
        while not aiter.done():
          arc = aiter.value()
          left_to_right[arc.ilabel][arc.olabel] += 1
          if not initial_only:
            right_to_left[arc.olabel][arc.ilabel] += 1
          aiter.next()
    mappings = set()
    # Finds the best match for a symbol, going in both directions. So if
    # language 1 /k/ matches to language 2 /s/, /o/ or /m/, and /s/ is most
    # common, then we propose /k/ -> /s/. Going the other way if language 1 /k/,
    # /t/ or /s/ matches to language 2 /s/, and /s/ is most common then we also
    # get /s/ -> /s/.
    for left in left_to_right:
      d = left_to_right[left]
      rights = sorted(d, key=d.get, reverse=True)[:max_allowed_mappings]
      for right in rights:
        mappings.add((left, right))
    if not initial_only:
      for right in right_to_left:
        d = right_to_left[right]
        lefts = sorted(d, key=d.get, reverse=True)[:max_allowed_mappings]
        for left in lefts:
          mappings.add((left, right))
    # Now build a new pared down aligner...
    new_aligner = py.Fst()
    s = new_aligner.add_state()
    new_aligner.set_start(s)
    new_aligner.set_final(s)
    new_aligner.set_input_symbols(symbols)
    new_aligner.set_output_symbols(symbols)
    for (ilabel, olabel) in mappings:
      new_aligner.add_arc(new_aligner.start(),
                            py.Arc(ilabel, olabel, 0, new_aligner.start()))
      if print_mappings:
        left = symbols.find(ilabel)
        right = symbols.find(olabel)
        left = left.replace("<epsilon>", "Ø")
        right = right.replace("<epsilon>", "Ø")
        print("{}\t->\t{}".format(left, right))
    self._aligner = new_aligner
    matched = 0
    # ... and realign with it, counting how many alignments succeed, and
    # computing how many homophones there are.
    input_homophones = collections.defaultdict(int) 
    output_homophones = collections.defaultdict(int) 
    matching_homophones = collections.defaultdict(int)
    for (p1, p2) in pairs:
      f1 = self._make_fst(p1, symbols)
      f2 = self._make_fst(p2, symbols)
      alignment = py.shortestpath(f1 * self._aligner * f2).topsort()
      if alignment.num_states() == 0:
        continue
      inp = []
      out = []
      n_deletions = 0
      n_insertions = 0
      for s in alignment.states():
        aiter = alignment.arcs(s)
        while not aiter.done():
          arc = aiter.value()
          if arc.ilabel:
            inp.append(symbols.find(arc.ilabel))
          else:
            inp.append("-")
            n_insertions += 1
          if arc.olabel:
            out.append(symbols.find(arc.olabel))
          else:
            out.append("-")
            n_deletions += 1
          aiter.next()
      inp = " ".join(inp).encode("utf8")
      input_homophones[inp] += 1
      out = " ".join(out).encode("utf8")
      output_homophones[out] += 1
      if n_deletions + n_insertions <= max_zeroes:
        matched += 1
        match = "{}\t{}".format(inp.decode("utf8"), out.decode("utf8"))
        print(match)
        matching_homophones[match] += 1
    # Counts the homophone groups --- the number of unique forms each of which
    # is assigned to more than one slot, for each language.
    inp_lang_homophones = 0
    for w in input_homophones:
      if input_homophones[w] > 1:
        inp_lang_homophones += 1
    out_lang_homophones = 0
    for w in output_homophones:
      if output_homophones[w] > 1:
        out_lang_homophones += 1
    print("HOMOPHONE_GROUPS:\t{}\t{}".format(inp_lang_homophones,
                                             out_lang_homophones))
    for match in matching_homophones:
      if matching_homophones[match] > 1:
        print("HOMOPHONE:\t{}\t{}".format(
          matching_homophones[match], match))
    return matched

  def _make_fst(self, string, symbols):
    fst = py.Fst()
    s = fst.add_state()
    fst.set_start(s)
    for c in string:
      label = symbols.find(c)
      next_s = fst.add_state()
      fst.add_arc(s, py.Arc(label, label, 0, next_s))
      s = next_s
    fst.set_final(s)
    fst.set_input_symbols(symbols)
    fst.set_output_symbols(symbols)
    return fst
      

def load_examples(f, parser):
  pairs = []
  with open(f) as stream:
    for line in stream:
      if line.startswith("#"):
        continue
      try:
        line = line.strip("\n").split("\t")
        pairs.append(tuple(map(parser, line)))
      except ValueError:
        continue
  return pairs


def main(unused_argv):
  parser = lambda x: x.split()
  pairs = load_examples(FLAGS.examples, parser)
  aligner = Aligner()
  print(aligner.compute_alignments(
    pairs,
    max_zeroes=FLAGS.max_zeroes,
    max_allowed_mappings=FLAGS.max_allowed_mappings,
    initial_only=FLAGS.initial_only))
  

if __name__ == "__main__":
  app.run(main)
  

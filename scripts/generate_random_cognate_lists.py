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


import aligner
import collections
import pynini as py
import random
import sys
import time


flags.DEFINE_string("list1", None,
                    "Path to first list, output of "
                    "generate_random_roots_from_lm.")
flags.DEFINE_string("list2", None,
                    "Path to second list, output of "
                    "generate_random_roots_from_lm.")
flags.DEFINE_string("far", "ie_to_pb/ie_to_pb.far",
                    "FAR containing the mapping rule "
                    "for the two lists")
flags.DEFINE_string("mapping_rule", "MAPPER",
                    "Mapping rule for the two lists")
flags.DEFINE_float("levenshtein_threshold", 3,
                   "Maximum 'wiggle-room' to allow for MAPPER.")
flags.DEFINE_integer("max_homophones", 5,
                     "Maximum number of any given homophone to allow")
flags.DEFINE_integer("number_of_etyma", 1000,
                     "How many etyma to produce")
flags.DEFINE_integer("number_of_experiments", 1000,
                     "How many experiments to run")
flags.DEFINE_integer("max_distinct_roots", -1,
                     "Maximum number of distinct roots to allow per language")
flags.DEFINE_bool("print_mappings", True,
                  "If using the alignment method, print found mapping rules.")
flags.DEFINE_bool("use_aligner", False, "Uses alignment method in aligner.py")

FLAGS = flags.FLAGS


class Roots:
  """Loads the root data and produces a list of etyma.
  """
  def __init__(self, filename, max_distinct_roots):
    entries = []
    with open(filename) as stream:
      for line in stream:
        root, count, _ = line.strip("\n").split("\t")
        count = int(count)
        entries.append((root, count))
    if max_distinct_roots > -1:
      random.shuffle(entries)
      entries = entries[:max_distinct_roots]
    self._entries = []
    for (root, count) in entries:
      self._entries += [root] * count

  def produce_etyma(self):
    """Produces etyma with no more than FLAGS.max_homophones homophones.

    Returns:
      List of FLAGS.number_of_etyma etyma.
    """
    random.shuffle(self._entries)
    netyma = 0
    etyma = []
    homophone_counts = collections.defaultdict(int)
    for root in self._entries:
      if homophone_counts[root] >= FLAGS.max_homophones:
        continue
      etyma.append(root)
      homophone_counts[root] += 1
      netyma += 1
      if netyma == FLAGS.number_of_etyma:
        break
    random.shuffle(etyma)
    return etyma


def produce_paired_etyma(roots1, roots2):
  """Produce a paired list of etyma.

  Args:
    roots1: A Roots class instance
    roots2: A Roots class instance
  Returns:
    zipped list of pairs of etyma
  """
  roots1_etyma = roots1.produce_etyma()
  roots2_etyma = roots2.produce_etyma()
  assert(len(roots1_etyma) == len(roots2_etyma))
  return zip(roots1_etyma, roots2_etyma)


def best_score(match):
  """Returns the best score of a match.

  Args:
    match: an FST
  Returns:
    float
  """
  for w in py.shortestpath(match).paths().weights():
    return float(w)
  return float("inf")


def run_experiments(roots1, roots2):
  """Runs FLAGS.number_of_experiments experiments.

  Args:
    roots1: A Roots class instance
    roots2: A Roots class instance
  """
  mapping_rule = py.Far(FLAGS.far)[FLAGS.mapping_rule]
  for i in range(FLAGS.number_of_experiments):
    zipped = produce_paired_etyma(roots1, roots2)
    success = 0
    for (e1, e2) in zipped:
      if best_score(e1 * mapping_rule * e2) <= FLAGS.levenshtein_threshold:
        print("{}\t{}".format(e1, e2))
        success += 1
    print("RUN:\t{}\t{}".format(i, success))
    sys.stdout.flush()


def run_experiments_with_aligner(roots1, roots2, initial_only=False):
  """Runs FLAGS.number_of_experiments experiments, using new aligner

  Note we assume that the input and output can be split on space!

  Args:
    roots1: A Roots class instance
    roots2: A Roots class instance
  """
  for i in range(FLAGS.number_of_experiments):
    zipped = [(c1.split(), c2.split())
                for (c1, c2) in produce_paired_etyma(roots1, roots2)]
    success = 0
    the_aligner = aligner.Aligner()
    success = the_aligner.compute_alignments(
      zipped,
      max_zeroes=FLAGS.max_zeroes,
      max_allowed_mappings=FLAGS.max_allowed_mappings,
      print_mappings=FLAGS.print_mappings,
      initial_only=initial_only)
    print("RUN:\t{}\t{}".format(i, success))
    sys.stdout.flush()


def main(unused_argv):
  roots1 = Roots(FLAGS.list1, FLAGS.max_distinct_roots)
  roots2 = Roots(FLAGS.list2, FLAGS.max_distinct_roots)
  if FLAGS.use_aligner:
    run_experiments_with_aligner(roots1, roots2, FLAGS.initial_only)
  else:
    run_experiments(roots1, roots2)


if __name__ == "__main__":
  flags.mark_flag_as_required("list1")
  flags.mark_flag_as_required("list2")
  app.run(main)
  

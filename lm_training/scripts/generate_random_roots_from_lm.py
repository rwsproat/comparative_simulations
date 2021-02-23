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

"""Generates random roots from an LM.
"""

from __future__ import division

from absl import app
from absl import flags

import collections
import pynini as py
import sys
import time

flags.DEFINE_string('far', None, 'Path to FAR')
flags.DEFINE_string('rule', None, 'Name of rule to use')
flags.DEFINE_integer('max_roots', 100000, 
                     'Maximum number of root types to generate')
flags.DEFINE_integer('npaths', 1000000, 'Number of paths to generate')
flags.DEFINE_bool('push', False, 'If true, push weights to initial')

FLAGS = flags.FLAGS


class Counter:
  """Statistics counter for list of strings.
  """
  def __init__(self, items):
    self._dict = collections.defaultdict(int)
    for item in items:
      self._dict[item] += 1
    if len(self._dict) > FLAGS.max_roots:
      new_dict = collections.defaultdict(int)
      d = self._dict
      for key in list(sorted(d, key=d.get, reverse=True))[:FLAGS.max_roots]:
        new_dict[key] = self._dict[key]
      self._dict = new_dict
    self._tot = sum(self._dict.values())

  def __repr__(self):
    d = self._dict
    t = self._tot
    return "\n".join(["{}\t{}\t{}".format(i, d[i], d[i] / t)
                      for i in sorted(d, key=d.get, reverse=True)])


def main(unused_argv):
  far = py.Far(FLAGS.far)
  fst = far[FLAGS.rule]
  # Note that we tried to push weights to the beginning so that we don"t get
  # spurious selection of "free" cases where the first byte of a UTF8 character
  # has no weight.
  #
  #   fst = py.push(fst, push_weights=True, to_final=False)
  #
  # However this seems to produce artifacts of its own like endless series of
  # Greek roots starting with "drai".  On the other hand without it PAN gets
  # endless roots starting with ñ.
  if FLAGS.push:
    fst = py.push(fst, push_weights=True, to_final=False)
  rand = py.randgen(fst,
                    npath=FLAGS.npaths,
                    seed=int(time.time()),
                    select="log_prob",
                    weighted=True)
  print(Counter([p for p in rand.paths().ostrings()]))


if __name__ == "__main__":
  flags.mark_flag_as_required("far")
  flags.mark_flag_as_required("rule")
  app.run(main)


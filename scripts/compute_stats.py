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

"""Computes R data from the output of generate_random_cognate_lists.py.

Also computes the likelihood of the observed number of cognates.
"""

from absl import app
from absl import flags

import collections
import math
import sys


flags.DEFINE_string("path", "",
                    "Path to output of generate_random_cognate_lists.py.")
flags.DEFINE_integer("arbitrary_max", 100,
                     "Arbitrary maximum number of cognates to guesstimate the "
                     "p value for the observed count.")
flags.DEFINE_integer("true_count", 49, "True number of cognates.")

FLAGS = flags.FLAGS


def poisson(lam, n, highest_k):
  """Generates probability of n or more cognates assuming Poisson distribution.

  Args:
    lam: The mean of the Poisson
    n: true cognates
    highest_k: bottom of range to generate
  Returns: area under the Poisson distribution for k >= n, or 0 if underflow.
  """
  try:
    p = 0
    loglam = math.log(lam)
    for k in range(n, highest_k):
      p += math.e ** (loglam * k - lam - math.log(math.factorial(k)))
    return p
  except ValueError:
    return 0


def compute_bins(path):
  """Computes the bin counts for numbers of cognates in each simulation.

  Args:
    path: Path to the output of generate_random_cognate_lists.py
  Returns:
    A histogram of the numbers of cognates.
  """
  bins = collections.defaultdict(int)
  with open(path) as stream:
    for line in stream:
      if line.startswith("RUN"):
        _, _, n_cognates = line.split()
        bins[int(n_cognates)] += 1
  return bins


def main(unused_argv):
  bins = compute_bins(FLAGS.path)
  mass = 0
  # Compute the mean, lambda
  lam = 0
  total = 0
  for n_cognates in sorted(bins):
    count = bins[n_cognates]
    print("{}\t{}".format(n_cognates, count))
    lam += count * n_cognates
    total += count
  lam /= total
  sys.stderr.write(
    ("Prob of k>={} cognates per Poisson "
     "estimate with lambda={}: {:.2e}\n").format(
    FLAGS.true_count,
    lam,
    poisson(lam, FLAGS.true_count, FLAGS.arbitrary_max)))


if __name__ == "__main__":
  app.run(main)
  

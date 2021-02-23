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

# Creates a list of potential "cognates" for a pair of languages.
#
# Assumes you have lingpy (http://lingpy.org/) and tabulate
# (https://pypi.org/project/tabulate/) installed.
#
# Example usage:
#
# python3 scripts/find_cognates_lingpy.py \
#   --language1=French
#   --language2=Hanunoo
#
# Output:
#
# cat /var/tmp/cognates/filtered_cognates_French_Hanunoo 
# ʒ u ʀ     s i r a ŋ

from absl import app
from absl import flags

import collections
import csv
import os

from lingpy import *
from tabulate import tabulate


flags.DEFINE_string("output_dir", "/var/tmp/cognates",
                    "Output directory")
flags.DEFINE_string("language1", None, "Language 1")
flags.DEFINE_string("language2", None, "Language 1")
flags.DEFINE_string("pairlist", "list_data/cognates.csv",
                    "Pathname of list of cognates extracted for "
                    "the languages in Section 6 of Blevins & Sproat")

FLAGS = flags.FLAGS


def make_pairlist(path, l1, l2):
  """Creates pair list for l1 and l2.

  Args:
    dir: output directory
    l1: language 1
    l2: language 2
  """
  pairlist = []
  with open(path) as stream:
    reader = csv.DictReader(stream)
    for row in reader:
      if row[l1] == "-" or row[l2] == "-":
        continue
      pairlist.append((row["GLOSS"], row[l1], row[l2]))
  return pairlist


def make_initial_cognate_tsv(dir, l1, l2, pairlist):
  """Collects initial "cognates" for l1 and l2.

  Args:
    dir: output directory
    l1: language 1
    l2: language 2
    pairlist: list of "cognate" pairs of l1, l2
  """
  filename = "{}/initial_cognates_{}_{}".format(dir, l1, l2)
  with open(filename, "w") as ostream:
    ostream.write("# {} <-> {}\n".format(l1, l2))
    ostream.write("ID\tTaxon\tGloss\tGlossID\tIPA\tTokens\n")
    id_ = 1
    gloss_id = 1
    for (gloss, p1, p2) in pairlist:
      if gloss == "GLOSS":
        continue
      ostream.write("#\n")
      ostream.write(
        "{}\t{}\t{}\t{}\t{}\t{}\n".format(
          id_, l1, gloss, gloss_id, p1.replace(" ", ""), p1))
      id_ += 1
      ostream.write(
        "{}\t{}\t{}\t{}\t{}\t{}\n".format(
          id_, l2, gloss, gloss_id, p2.replace(" ", ""), p2))
      id_ += 1
      gloss_id += 1
    

def collect_potential_cognates(dir, l1, l2, threshold=0.55, runs=10000):
  """Collects potential cognates for l1 and l2.

  Args:
    dir: output directory
    l1: language 1
    l2: language 2
    threshold: threshold for acceptance of cognate, distance from 
      lex.align_pairs
    runs: number of runs to perform
  """
  filename = "{}/initial_cognates_{}_{}".format(dir, l1, l2)
  lex = LexStat(filename)
  lex.get_scorer(runs=runs)
  table = []
  # He sorts the keys :), so we have to present them in sorted order for keying
  # into his tables.
  if l2 < l1:
    L1, L2 = l2, l1
  else:
    L1, L2 = l1, l2
  initial_list_len = 0
  for key, (idxA, idxB) in enumerate(lex.pairs[L1, L2]):
    almA, almB, dst = lex.align_pairs(idxA, idxB, mode="overlap", pprint=False)
    initial_list_len += 1
    if dst <= threshold:
      table += [[
      key+1, 
      lex[idxA, "concept"], 
      lex[idxA, "tokens"], 
      lex[idxB, "tokens"], 
      round(dst, 2)]]
  # Eschew writing this out in tabular format and instead just write out l1 and
  # l2, one "cognate" per line, so that this can be used directly by
  #
  # generate_random_cognate_lists.sh
  with open("{}/filtered_cognates_{}_{}".format(dir, l1, l2), "w") as stream:
    for row in table:
      _, _, l1, l2, _ = row
      stream.write("{}\t{}\n".format(" ".join(l1), " ".join(l2)))


def main(unused_argv):
  try:
    os.mkdir(FLAGS.output_dir)
  except FileExistsError:
    pass
  pairlist = make_pairlist(FLAGS.pairlist,
                           FLAGS.language1,
                           FLAGS.language2)
  make_initial_cognate_tsv(FLAGS.output_dir,
                           FLAGS.language1,
                           FLAGS.language2,
                           pairlist)  
  collect_potential_cognates(FLAGS.output_dir,
                             FLAGS.language1,
                             FLAGS.language2)

if __name__ == "__main__":
  flags.mark_flag_as_required("language1")
  flags.mark_flag_as_required("language2")
  app.run(main)

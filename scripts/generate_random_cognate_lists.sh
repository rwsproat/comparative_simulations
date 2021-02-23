#!/bin/bash
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

# Example usage:
#
# scripts/generate_random_cognate_lists.sh \
#    data/grouping_LJ.tsv
#    data/random_roots_ie.tsv
#    data/random_roots_pb.tsv
#
SWADESH=$1
LANG1=$2
LANG2=$3
MAX_ZEROES=1
MAX_ALLOWED_MAPPINGS=2
# We used 1000 in the experiments reported in Blevins & Sproat, but 100 is
# generally sufficient.
NEXP=1000
# Computes the number of pairs from the Swadesh that are found by the alignment
# algorithm. We use this as the "true" count of the Swadesh cognates.
TRUE_COUNT=`python3 scripts/aligner.py \
    --examples="${SWADESH}" \
    --max_zeroes="${MAX_ZEROES}" \
    --max_allowed_mappings="${MAX_ALLOWED_MAPPINGS}" | tail -1`
echo "True count matching alignment against gold Swadesh is ${TRUE_COUNT}"
# Runs the simulation
python3 scripts/generate_random_cognate_lists.py \
    --list1="${LANG1}" \
    --list2="${LANG2}" \
    --max_distinct_roots=9000 \
    --number_of_experiments="${NEXP}" \
    --use_aligner=1 \
    --max_zeroes="${MAX_ZEROES}" \
    --max_allowed_mappings="${MAX_ALLOWED_MAPPINGS}" \
    --print_mappings=1 \
    --number_of_etyma=200 > scratch/tmp
# Generates a matrix that can be loaded into, say, R, and computes the Poisson
# probability of the "true" count given the simulations.
python3 scripts/compute_stats.py \
    --path=scratch/tmp \
    --true_count="${TRUE_COUNT}" \
    >scratch/tmp.mat \
    2>scratch/tmp.poisson
cat scratch/tmp.poisson

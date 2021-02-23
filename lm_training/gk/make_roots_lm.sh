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
set -v
../scripts/buildlm.sh gkroots
awk '$2>0 {print $1 "\t" $1}' gkroots.syms >gklmsyms.tsv
mv lm_nosyms.fst gk_lm_nosyms.fst
thraxmakedep gkroots_lm.grm
make
python3 ../scripts/generate_random_roots_from_lm.py \
    --far=gkroots_lm.far \
    --rule=GKROOTS_LM >random_roots_gk.tsv

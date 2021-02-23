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
K=$1
ngramsymbols <${K}.txt >${K}.syms
farcompilestrings -symbols=${K}.syms -keep_symbols=1 ${K}.txt >${K}.far
ngramcount --order=3 ${K}.far >${K}.cnts
ngrammake ${K}.cnts >${K}.mod
fstprint --numeric ${K}.mod | fstcompile >lm_nosyms.fst
rm -f ${K}.far ${K}.cnts

#!/usr/bin/env python3

# Split Kubernetes manifests by filtering objects

import os
import sys
import argparse
import re
import yaml

parser = argparse.ArgumentParser(description='Kubernetes YAML filter')
parser.add_argument('input',help='Input manifest')
parser.add_argument('--only-kinds', '-k', nargs='+', default=[], help='only keep objects of the specified Kind(s)')
parser.add_argument('--skip-kinds', '-K', nargs='+', default=[], help='skip objects of the specified Kind(s)')
parser.add_argument('--only-names', nargs='+', default=[], help='keep objects whose name matches the regular expression(s)')

args = parser.parse_args()

# lowercase args
for n, v in enumerate(args.only_kinds):
  args.only_kinds[n] = v.lower()
for n, v in enumerate(args.skip_kinds):
  args.skip_kinds[n] = v.lower()

# known objects
knownObjects = set()
def objectIdentifier(yml_dict):
  h = ''

  h += yml_dict.get('kind', '')

  meta = yml_dict.get('metadata', None)
  if meta:
    h += ':' + meta.get('namespace','(unset)') + '/' + meta.get('name','(unnamed)')
  
  return h


with open(args.input) as f:
  yml_document_all = yaml.safe_load_all(f)
  
  for yml_document in yml_document_all:
    if yml_document is None:
      continue

    if yml_document['kind'].lower() in args.skip_kinds:
      continue

    if len(args.only_kinds) > 0 and yml_document['kind'].lower() not in args.only_kinds:
      continue

    metadata = yml_document.get('metadata', None)

    # if only_names regexps are defined
    if metadata and len(args.only_names) > 0:
      match = False
      for pattern in args.only_names:
        if re.search(pattern, metadata.get('name', '')):
          match = True
          break
      
      if not match:
        continue # skip if no regexp matches part of this name

    oi = objectIdentifier(yml_document)
    if oi in knownObjects:
      print("Skipped a duplicate object "+oi, file=sys.stderr)
      continue

    knownObjects.add(oi)
    #print(oi, file=sys.stderr)

    print(yaml.dump(yml_document), end="---"+os.linesep)

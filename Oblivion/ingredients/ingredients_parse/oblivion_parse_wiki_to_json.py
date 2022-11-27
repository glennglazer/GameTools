#!/usr/bin/python3

"""
File: oblivion_parse_wiki_to_json.py
Author: Glenn Glazer

Utility to parse wikitables into JSON for loading into a db.

File is expected to look like this:

|
|Alkanet Flower
|0.1
|1
|Alkanet
|Restore Intelligence,Resist Poison,Light,Damage Fatigue
|0003365C

with wiki/html formatting stripped out. If there are multiple IDs, "foo</br>bar" should be "foo,bar"
for better readability, though the parsing will work either way

Output JSON format:

{"name" : Alkanet Flower", 
 "weight": 0.1,
 "value": 1,
 "first": "Restore Intelligence",
 "second": "Resist Poison",
 "third": "Light",
 "fourth": "Damage Fatigue",
 "ID": "0003365C"
}

"""

import argparse
import json
import os.path as op
import sys

from pprint import pprint

MAX_NUMBER_OF_EFFECTS = 4
NUMBER_OF_WIKI_LINES = 7

# just uniform one from position zero, other pipes are handled later
def remove_pipe(value: str) -> str:
    if value is not None and "|" in value:
        return value.lstrip('|')
    else:
        return value

# if the name includes the wiki pipe trick use the name not the wiki link
# e.g., "Alocasia Fruit (Oblivion)|Alocasia Fruit" -> "Alocasia Fruit"
def remove_wiki_link(value: str) -> str:
    if value is not None and "|" in value:
        return value.split("|")[1]
    else:
        return value

# this assumes a well-formed file per expectations above
# if the entries seem messed up, check the file format
def parse(infile: str, verbose: bool = False) -> dict:
    rv = []
    if not op.exists(infile):
        return None
    
    with open(infile, mode='r') as inf:
        lines = inf.read().splitlines()
        # an entry has exactly 9 properties, if the list is 0 < len < 9 at the end, some entry(ies) are incorrectly formatted
        while len(lines) >= NUMBER_OF_WIKI_LINES:
            # skip the blank at line[0] and sources at line[4], not needed
            name = remove_wiki_link(remove_pipe(lines[1]))
            weight = float(remove_pipe(lines[2]))
            value = int(remove_pipe(lines[3]))
            # Unlike the wiki page for Morrowind, all of the effects are in one column
            # search and replace <br > to comma separated list which we then None fill to four
            effects_string = remove_wiki_link(remove_pipe(lines[5])).rstrip()
            effects = effects_string.split(',')
            number_of_effects = len(effects)
            for _ in range(0, MAX_NUMBER_OF_EFFECTS - number_of_effects):
                effects.append(None)
            first, second, third, fourth = effects
            ID = remove_pipe(lines[6]).rstrip()
            
            entry = {'name': name, 'weight': weight, 'value': value,
                     'first': first, 'second': second, 'third': third, 'fourth': fourth,
                     'ID': ID}
            
            for effect in ('name', 'first', 'second', 'third', 'fourth'):
                if entry[effect] is not None:
                    entry[effect] = entry[effect].rstrip()

            rv.append(entry)
            if verbose:
                print(f"entry: {entry} rv so far: {rv}\n")
            # move down to the next entry
            lines = lines[NUMBER_OF_WIKI_LINES:]
        return rv

def write_file(parsed: dict, outfile: str) -> bool:
    # if the file exists, overwrite it
    with open(outfile, mode='w') as of:
        json.dump(parsed, of)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("infile", help="absolute path to file to read wiki formatting from")
    parser.add_argument("outfile", help="absolute path to file to (over) write JSON to")
    parser.add_argument("-v", "--verbose", help="debug output", action="store_true")
    args = parser.parse_args()
    
    if not args.infile or not args.outfile:
        parser.print_usage()
        sys.exit(1)
    
    parsed = parse(args.infile, args.verbose)
    if args.verbose:
        pprint(parsed)
    
    if parsed == {}:
        print("Error parsing wiki text file, check formatting of entries.")
        sys.exit(1)
    
    write_file(parsed, args.outfile)
    
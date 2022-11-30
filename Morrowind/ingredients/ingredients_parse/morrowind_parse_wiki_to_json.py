#!/usr/bin/python3

"""
File: morrowind_parse_wiki_to_json.py
Author: Glenn Glazer

Utility to parse wikitables into JSON files for loading into a db.

File is expected to look like this:

|
|Alit Hide 
|1.0 
|5 
|Drain Intelligence 
|Resist Poison (Morrowind)|Resist Poison 
|Telekinesis (Morrowind)|Telekinesis 
|Detect Animal 
|ingred_alit_hide_01

with wiki/html formatting stripped out. If there are multiple IDs, "foo</br>bar" should be "foo, bar"
for better readability, though the parsing will work either way

Output JSON format for ingredients file:

{"name" : "Alit Hide", 
 "weight": 1.0,
 "value": 5,
 "ID": "ingred_alit_hide_01"
}

Output JSON format for effects file:

{"name" : "Alit Hide", 
 "effect": "Drain Intelligence"
}

"""

import argparse
import json
import os.path as op
import sys

from pprint import pprint

NUMBER_OF_WIKI_LINES = 9

# just uniform one from position zero, other pipes are handled later
def remove_pipe(value: str) -> str:
    if value is not None and "|" in value:
        return value.lstrip('|')
    else:
        return value

# if the name includes the wiki pipe trick use the name not the wiki link
# e.g., "Bungler's Bane (Morrowind)|Bungler's Bane" -> "Bungler's Bane"
def remove_wiki_link(value: str) -> str:
    if value is not None and "|" in value:
        return value.split("|")[1]
    else:
        return value

# wiki uses - for no effect at this level (not all have four effects)
# JSON wants null, so write None
def dash_to_null(entry: str) -> str:
    if '-' in entry:
        return None
    else:
        return entry

# this assumes a well-formed file per expectations above
# if the entries seem messed up, check the file format
def parse(infile: str, verbose: bool = False) -> dict:
    ingredients = []
    effects = []
    
    if not op.exists(infile):
        return {}, {}
    
    with open(infile, mode='r') as inf:
        lines = inf.read().splitlines()
        # an entry has exactly 9 properties, if the list is 0 < len < 9 at the end, some entry(ies) are incorrectly formatted
        while len(lines) >= NUMBER_OF_WIKI_LINES:
            # skip the blank at line[0], not needed
            name = remove_wiki_link(remove_pipe(lines[1])).rstrip()
            weight = float(remove_pipe(lines[2]))
            value = int(remove_pipe(lines[3]))
            first = remove_wiki_link(remove_pipe(dash_to_null(lines[4])))
            second = remove_wiki_link(remove_pipe(dash_to_null(lines[5])))
            third = remove_wiki_link(remove_pipe(dash_to_null(lines[6])))
            fourth = remove_wiki_link(remove_pipe(dash_to_null(lines[7])))
            ID = remove_pipe(lines[8]).rstrip()
            
            ingredients_entry = {'name': name, 'weight': weight, 'value': value, 'ID': ID}
            ingredients.append(ingredients_entry)

            effects_list = [first, second, third, fourth]
            
            for effect in effects_list:
                if effect is not None:
                    effect = effect.rstrip()
                effects.append({'name': name, 'effect': effect,})
            
            if verbose:
                print(f"ingredients entry: {ingredients_entry}\n")
                print(f"ingredients so far: {ingredients}\n")
                print(f"effects list: {effects_list}")
                print(f"effects so far: {effects}\n")
            # move down to the next entry
            lines = lines[NUMBER_OF_WIKI_LINES:]
        return ingredients, effects

def write_file(parsed: dict, outfile: str) -> bool:
    # if the file exists, overwrite it
    with open(outfile, mode='w') as of:
        json.dump(parsed, of)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("infile", help="absolute path to file to read wiki formatting from")
    parser.add_argument("ingredient_file", help="absolute path to file to (over) write ingredient JSON to")
    parser.add_argument("effects_file", help="absolute path to file to (over) write ingredient effects JSON to")
    parser.add_argument("-v", "--verbose", help="debug output", action="store_true")
    args = parser.parse_args()
    
    if not args.infile or not args.ingredient_file or not args.effects_file:
        parser.print_usage()
        sys.exit(1)
    
    parsed_ingredients, parsed_effects = parse(args.infile, args.verbose)
    if args.verbose:
        pprint(parsed_ingredients)
        pprint(parsed_effects)
    
    if parsed_ingredients == {} or parsed_effects == {}:
        print("Error parsing wiki text file, check formatting of entries.")
        sys.exit(1)
    
    write_file(parsed_ingredients, args.ingredient_file)
    write_file(parsed_effects, args.effects_file)
    
    
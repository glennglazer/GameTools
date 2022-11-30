#!/usr/bin/python3

"""
File: oblivion_parse_wiki_to_json.py
Author: Glenn Glazer

Utility to parse wikitables into JSON files for loading into a db.

File is expected to look like this:

|
|Alkanet Flower
|0.1
|1
|Alkanet
|Restore Intelligence,Resist Poison,Light,Damage Fatigue
|0003365C

with wiki/html formatting stripped out. If there are multiple IDs, "foo</br>bar" should be "foo, bar"
for better readability, though the parsing will work either way

Output JSON format for ingredients file:

{"name" : "Alkanet Flower", 
 "weight": 0.1,
 "value": 1,
 "ID": "0003365C"
}

Output JSON format for effects file:

{"name" : "Alkanet Flower", 
 "effect": "Restore Intelligence"
}

"""

import argparse
import json
import os.path as op
import sys

from pprint import pprint

NUMBER_OF_WIKI_LINES = 7
MAX_NUMBER_OF_EFFECTS = 4

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
    ingredients = []
    effects = []
    
    if not op.exists(infile):
        return {}, {}
    
    with open(infile, mode='r') as inf:
        lines = inf.read().splitlines()
        # an entry has exactly 7 properties, if the list is 0 < len < 7 at the end, some entry(ies) are incorrectly formatted
        while len(lines) >= NUMBER_OF_WIKI_LINES:
            # skip the blank at line[0] and sources at line[4], not needed
            name = remove_wiki_link(remove_pipe(lines[1])).rstrip()
            weight = float(remove_pipe(lines[2]))
            value = int(remove_pipe(lines[3]))          
            ID = remove_pipe(lines[6]).rstrip()
            
            ingredients_entry = {'name': name, 'weight': weight, 'value': value, 'ID': ID}
            ingredients.append(ingredients_entry)
            
            # Unlike the wiki page for Morrowind, all of the effects are in one column
            # search and replace <br > to comma separated list which we then None fill to four
            effects_string = remove_wiki_link(remove_pipe(lines[5])).rstrip()
            effects_list = effects_string.split(',')
            number_of_effects = len(effects_list)
            for _ in range(0, MAX_NUMBER_OF_EFFECTS - number_of_effects):
                effects_list.append(None)            
            
            for effect in effects_list:
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
    
    
#!/usr/bin/python3

"""
File: morrowind_parse_enchant_csv_to_json.py
Author: Glenn Glazer

Utility to parse CSV files into JSON files for loading into a db.
Assumes there are four files to be read: armor, books, clothing, weapons
"""

import argparse
import csv
import json
import os.path as op
import sys

FILE_PREFIXES = ['armor', 'books', 'clothing', 'weapons']

def write_file(parsed: list, outfile: str) -> bool:
    # if the file exists, overwrite it
    with open(outfile, mode='w') as of:
        json.dump(parsed, of)
        
def check_for_files(in_dir: str) -> bool:
    rv = True
    for prefix in FILE_PREFIXES:
        rv = rv and op.exists(in_dir + '/' + prefix + '.csv')
    return rv

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("in_dir", help="absolute path to directory to read CSV files from")
    parser.add_argument("out_dir", nargs='?', help="absolute path to directory to (over) write enchanting JSON to. Defaults to in_dir.")
    args = parser.parse_args()
    in_dir = args.in_dir
    out_dir = args.out_dir
    
    if not in_dir or not op.exists(args.in_dir):
        print(f"Read directory not given or does not exist: {in_dir}")
        parser.print_usage()
        sys.exit(1)
    elif not check_for_files(in_dir):
        print(f"One or more of {FILE_PREFIXES} CSV files missing from specified input directory {in_dir}")
    
    if not out_dir:
        out_dir = in_dir
    else:
        if not op.exists(out_dir):
            print(f"Specified output directory does not exist: {out_dir}")
            parser.print_usage()
            sys.exit(1)
    
    for item_type in FILE_PREFIXES:
        item_read = f"{in_dir}/{item_type}.csv"
        item_write = f"{out_dir}/{item_type}.json"
        item_list = []
        
        # Given the arg testing, we are guaranteed these exist. Format, validity, etc. is not.
        with open(item_read, newline='') as item_file:
            reader = csv.DictReader(item_file)
            try:
                for row in reader:
                    item_list.append(row)
            except csv.Error as e:
                print(f"Error parsing {row} in {item_read}: {e}")
                sys.exit(1)
            
        write_file(item_list, item_write)
            
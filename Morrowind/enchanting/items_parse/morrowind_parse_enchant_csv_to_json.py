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
        
def check_for_files(inDir: str) -> bool:
    rv = True
    for prefix in FILE_PREFIXES:
        rv = rv and op.exists(inDir + '/' + prefix + '.csv')
    return rv

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("inDir", help="absolute path to directory to read CSV files from")
    parser.add_argument("outDir", nargs='?', help="absolute path to directory to (over) write enchanting JSON to. Defaults to inDir.")
    args = parser.parse_args()
    inDir = args.inDir
    outDir = args.outDir
    
    if not inDir or not op.exists(args.inDir):
        print(f"Read directory not given or does not exist: {inDir}")
        parser.print_usage()
        sys.exit(1)
    elif not check_for_files(inDir):
        print(f"One or more of {FILE_PREFIXES} CSV files missing from specified input directory {inDir}")
    
    if not outDir:
        outDir = inDir
    else:
        if not op.exists(outDir):
            print(f"Specified output directory does not exist: {outDir}")
            parser.print_usage()
            sys.exit(1)
    
    for item_type in FILE_PREFIXES:
        item_read = f"{inDir}/{item_type}.csv"
        item_write = f"{outDir}/{item_type}.json"
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
            
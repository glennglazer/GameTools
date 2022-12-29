#!/usr/bin/python3

"""
File: create_morrowind_enchant_items.py
Author: Glenn Glazer

Utility to create/update enchantable item database tables from JSON"""

import argparse
import json
import os.path as op
import pandas as pd
import sqlite3
import sys

FILE_PREFIXES = ['armor', 'books', 'clothing', 'weapons', 'soul_gems', 'magic_effects', 'magic_schools']

def check_for_files(in_dir: str) -> bool:
    rv = True
    for prefix in FILE_PREFIXES:
        rv = rv and op.exists(in_dir + '/' + prefix + '.json')
    return rv

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("json_dir", help="absolute path to directory to read enchanting item JSON data from")
    parser.add_argument("db", help="absolute path to sqlite db file")
    args = parser.parse_args()
    json_dir = args.json_dir
    db_location = args.db
    
    if not json_dir or not db_location:
        print(f"Not enough parameters. json_dir: {json_dir} and db_location: {db_location}")
        parser.print_usage()
        sys.exit(1)
        
    if not check_for_files(json_dir):
        print(f"One or more JSON files in {FILE_PREFIXES} do not exist in {json_dir}")
        
    # Pandas will create the table if it doesn't exist
    conn = sqlite3.connect(args.db)
    cur = conn.cursor()    
    
    for item_type in FILE_PREFIXES:
        item_read = f"{json_dir}/{item_type}.json"
        table_name = f"morrowind_enchant_{item_type}"
    
        # import data file, make it into a DataFrame
        with open(item_read) as jf:
            try:
                data = json.load(jf)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON file: {e.msg} at line {e.lineno} and column {e.colno}")
                sys.exit(1)
        
        df = pd.DataFrame(data)
        
        # On the other hand, it doesn't have REPLACE INTO or INSERT ON DUPLICATE UPDATE, so DELETE then append. Sigh.
        exists = cur.execute(f"SELECT name FROM sqlite_master WHERE name='{table_name}'").fetchone()
        if exists is not None:
            IDs = [(d['ID'], ) for d in data]
            cur.executemany(f'DELETE FROM {table_name} WHERE ID = ?', IDs)
            conn.commit()
            
        # populate the table
        # if_TABLE_exists, not if_ROW_exists
        df.to_sql(table_name, conn, if_exists='append', method='multi')
        
        # if the table didn't exist before, add the PK
        if exists is None:
            index = f"m_e_{item_type}"
            result = cur.execute(f"CREATE UNIQUE INDEX {index} ON {table_name} (ID)")
            conn.commit()
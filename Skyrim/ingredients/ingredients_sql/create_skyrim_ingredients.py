#!/usr/bin/python3

"""
File: create_skyrim_ingredients.py
Author: Glenn Glazer

Utility to create/update ingredients database table from JSON"""

import argparse
import json
import pandas as pd
import sqlite3
import sys

TABLE_NAME = 'skyrim_ingredients'

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("json_file", help="absolute path to file to read ingredients JSON data from")
    parser.add_argument("db", help="absolute path to sqlite db file")
    parser.add_argument("-v", "--verbose", help="debug output", action="store_true")
    args = parser.parse_args()
    
    if not args.json_file or not args.db:
        parser.print_usage()
        sys.exit(1)
    
    # import data file, make it into a DataFrame
    with open(args.json_file) as jf:
        try:
            data = json.load(jf)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON file: {e.msg} at line {e.lineno} and column {e.colno}")
            sys.exit(1)
        
    df = pd.DataFrame(data)
    
    # Pandas will create the table if it doesn't exist
    conn = sqlite3.connect(args.db)
    cur = conn.cursor()
    
    # On the other hand, it doesn't have REPLACE INTO or INSERT ON DUPLICATE UPDATE, so DELETE then append. Sigh.
    exists = cur.execute(f"SELECT name FROM sqlite_master WHERE name='{TABLE_NAME}'").fetchone()
    if exists is not None:
        names = [(d['name'], ) for d in data]
        cur.executemany(f'DELETE FROM {TABLE_NAME} WHERE name = ?', names)
        conn.commit()
    
    # populate the table
    # if_TABLE_exists, not if_ROW_exists
    df.to_sql(TABLE_NAME, conn, if_exists='append', method='multi')
    
    # if the table didn't exist before, add the PK
    if exists is None:
        result = cur.execute(f"CREATE UNIQUE INDEX s_i_name ON {TABLE_NAME} (name)")
        conn.commit()

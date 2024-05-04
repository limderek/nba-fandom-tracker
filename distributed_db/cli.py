from datetime import datetime
import json
from typing import Optional
from db.provisioner import DatabaseProvisioner
from db.manager import DatabaseManager
from db.exceptions import DateOutOfRangeError, EmptyMetadataError, DuplicateDataError
from constants import METADATA_LOCAL, TERRAFORM_DIR, AZURE_METADATA_PATH, METADATA_COPY
from pprint import pprint
import argparse
import pymysql
import pandas as pd
from tabulate import tabulate

md = AZURE_METADATA_PATH

dbp = DatabaseProvisioner(md, TERRAFORM_DIR)
dbm = DatabaseManager(md)

def init_parsers():
    parser = argparse.ArgumentParser(description='Distributed DB Management CLI Tool')
    subparsers = parser.add_subparsers(dest='command')
    
    # python3 cli.py insert <table> [-j] <json file> [-d] <manual input>
    insert_parser = subparsers.add_parser('insert', help='Insert records across tables in the distributed database.', usage='python3 cli.py insert <table> [-j] <json file> [-d] <manual input>')
    insert_parser.add_argument('table', choices=['users', 'prefs', 'nba'], help='Name of the table')
    insert_parser.add_argument('-j', '--json', required=False, help='Indicates the data is a JSON file name')
    insert_parser.add_argument('-d', '--data', nargs='+', required=False, type=str, help='Indicates that user will type out all records to insert')
    
    # python3 cli.py delete <table> [-d] <database> [-c] <condition>
    delete_parser = subparsers.add_parser('delete', help='Delete records across tables in the distributed database.', usage='python3 cli.py delete <table> [-d] <database> [-c] <condition>')
    delete_parser.add_argument('table', choices=['users', 'prefs', 'nba'], help='Name of the table to delete from.')
    delete_parser.add_argument('-d', '--database', help='Database to delete from', required=False)
    delete_parser.add_argument('-c', '--condition', help='Condition for deletion', required=False)
    
    # python cli.py update <table> <set> <condition> [-d] <database>
    update_parser = subparsers.add_parser('update', help='Update records in the distributed database.', usage='python cli.py update <table> <set> <condition> [-d] <database>')
    update_parser.add_argument('table', choices=['users', 'prefs', 'nba'], help='Name of the table to update.')
    update_parser.add_argument('set', type=str, help='Values to set')
    update_parser.add_argument('-c', '--condition', type=str, help='Condition for the update.', required=False)
    update_parser.add_argument('-d', '--database', help='Database to update in', required=False)

    # python cli.py select [-t] <table> [-n] <'team' | 'player'>
    select_parser = subparsers.add_parser('select', help='Selects all data from a table across the distributed database.')
    select_parser.add_argument('-t', '--table', type=str, choices=['users', 'prefs', 'nba'], help='Name of the table to SELECT * from.', required=False)
    select_parser.add_argument('-n', '--nbaType', type=str, choices=['teams', 'players'], help='Select Nba teams, or players')
    # select_parser.add_argument('-j', '--join', type)

    # python3 cli.py breakdown [--type] <team | player> [--level] <fandom level> [--name] <name>
    breakdown_parser = subparsers.add_parser('breakdown', help='Show the breakdown of fandoms stored in the distributed database', usage='python3 cli.py count [--type] <team | player> [--level] <fandom level> [--name] <name>')
    breakdown_parser.add_argument('--type', choices=['team', 'player'], required=False)
    breakdown_parser.add_argument('--level', choices=['favorite', 'bandwagon', 'rival', 'hates'], required=False)
    breakdown_parser.add_argument('--name', required=False)
    
    # python3 cli.py user <user>
    user_parser = subparsers.add_parser('user', help='Shows all data associated with a user name.')
    user_parser.add_argument('user')
    
    # python3 cli.py metadata <metadata>
    metadata_parser = subparsers.add_parser('metadata', help='Displays the metadata for the distributed database')
    metadata_parser.add_argument('-v', '--verbose', required=False, action='store_true')
    # metadata_parser.add_argument('metadata')
    
    # python3 cli.py init <num_dbs>
    init_parser = subparsers.add_parser('init', usage='python3 cli.py init <num_dbs>')
    init_parser.add_argument('dbs', type=int)
    
    # python3 cli.py destroy
    destroy_parser = subparsers.add_parser('destroy')
    
    # python3 cli.py expand <num_dbs>
    expand_parser = subparsers.add_parser('expand', help='Adds new set of databases to the distributed database')
    expand_parser.add_argument('num_dbs', type=int, help='Number of databases in this range')
    

    return parser
    

def insert(table, data: list[dict]):
    """
    nba: inserts all data into all databases
    user/prefs: partitions
    """
    metadata = dbm.read_metadata()
    
    if table == 'nba':
        for db in metadata['Connections']:
            for item in data:
                try:
                    dbm.insert_one(item, table, metadata['Connections'][db])
                except DuplicateDataError as err:
                    msg = f'Duplicate entry for {item}'
                    print(msg)
            
    elif table == 'users':
        """
        for item in data:
            creds = dbm.locate_db()
                dbm.insert_one(item, 'users', creds)
        """
        for record in data:
            try:
                # print(record)
                username = record['user']
                date = record['date']
                db = dbm.locate_db(metadata, date, username)
                dbm.insert_one(record, table, metadata['Connections'][db])
            except DuplicateDataError as err:
                    msg = f'Duplicate entry for {record}'
                    print(msg)
            except KeyError as err:
                print(err)
                print('Insert a record in the form of {"user": <user>, "date": <date>, "password": <password>}')
            # except pymysql.err.IntegrityError as err:
            #     print(err)

    elif table == 'prefs':
        """
        for item in data:
            creds = dbm.locate_db()
                dbm.insert_one(item, 'prefs', creds)
        """
        for record in data:
            try:
                print(f'{table.upper()}: {record}')
                username = record['user']
                date = record['date']
                db = dbm.locate_db(metadata, date, username)
                dbm.insert_one(record, table, metadata['Connections'][db])
            except DuplicateDataError as err:
                    msg = f'Duplicate entry for {record}'
                    print(msg)
            except KeyError as err:
                print('Insert a record in the form of {"user": <user>, "date": <date>, "nba_entity": <nba_entity>, "preference": <preference>}')
                raise err
            except pymysql.err.IntegrityError as err:
                if err.args[0] == 1452:
                    print('Please insert user or nba data first before inserting preferences.')
                   
                    
def delete(table, db: Optional[str] = None, condition: Optional[str] = None):
    metadata = dbm.read_metadata()
    
    if not db:
        delete_from_all = input('Are you sure you want to delete from all databases? (Y/n): ')
        if delete_from_all == 'Y':
            for db in metadata['Connections']:
                dbm.delete_from_one(table, metadata['Connections'][db], condition)
    else:
        dbm.delete_from_one(table, metadata['Connections'][db], condition)            
             
def update(table, set_clause, db: Optional[str] = None, condition: Optional[str] = None):
    metadata = dbm.read_metadata()     
    
    if not db:
        update_in_all = input('Are you sure you want to make this update in all databases? (Y/n): ')
        if update_in_all == 'Y':
            for c in metadata['Connections']:
                dbm.update_in_one(table, metadata['Connections'][c], set_clause, condition=condition) 
    
    else:
        dbm.update_in_one(table, metadata['Connections'][db], set_clause, condition=condition) 

             
def select_all(field):
    metadata = dbm.read_metadata()
    
    table_options = {
        'prefs': 'Preferences',
        'users': 'Users',
        'nba': 'Nba',
        'teams': 'team',
        'players': 'player'
    }
    
    cols = {
        'users': ['user, date', ['user', 'date']],
        'nba': ['name, type', ['name', 'type']],
        'prefs': ['user, nba_entity, preference', ['user', 'nba', 'preference']],
        'teams': ['', ['team_name']],
        'players': ['', ['player_name']]
    }
    
    if field in ['teams', 'players']:
        query = f"""
            SELECT name 
            FROM nba
            WHERE type='{table_options[field]}';
        """
    else:
        query = f"""
            SELECT {cols[field][0]} 
            FROM {table_options[field]};
        """

    
    all_users = []
    for db in metadata['Connections']:
        output = dbm.query_one( query, metadata['Connections'][db])
        all_users.extend(output)
        
    if field in ['nba', 'teams', 'players']:
        all_users = set(all_users)
    
    num_rows = len(all_users)
    return num_rows, tabulate(all_users, headers=cols[field][1], tablefmt='psql')


def select_fandom(nba_name: Optional[str] = None, nba_type: Optional[str]= None, level: Optional[str]= None):
    
    metadata = dbm.read_metadata()
    
    pref_label = {
        'favorite': 'Fans',
        'bandwagon': 'Bandwagoners',
        'rival': 'Haters'
    }
    params=None
    
    if not (nba_name and nba_type and level):
        query = f"""
            WITH fandom (type, name, pref, cnt) as (
                SELECT Nba.type, Preferences.nba_entity, Preferences.preference, COUNT(*) as cnt
                FROM Preferences, Users, Nba
                WHERE Preferences.user = Users.user
                AND Preferences.nba_entity = Nba.name
                GROUP BY Preferences.nba_entity, Preferences.preference
                ORDER BY cnt DESC
            )
            SELECT * FROM fandom;
        """
        title = 'Full NBA Breakdown'
        columns = ['type', 'name', 'pref', 'cnt']
        
    if nba_type and (not (nba_name and level)): # select either all the the teams or all the players
        query = f"""
            WITH fandom (type, name, pref, cnt) as (
                SELECT Nba.type, Preferences.nba_entity, Preferences.preference, COUNT(*) as cnt
                FROM Preferences, Users, Nba
                WHERE Preferences.user = Users.user
                AND Preferences.nba_entity = Nba.name
                GROUP BY Preferences.nba_entity, Preferences.preference
                ORDER BY cnt DESC
            )
            SELECT name, cnt FROM fandom
            WHERE type = %s;
        """
        params = (nba_type)
        title = f'{nba_type} Fandom Breakdown'
        columns = ['name', 'cnt']
        
    if nba_name and (not(nba_type and level)):  # select the specific entity in question (ex. the fandom of the spurs)
        query = f"""
            WITH fandom (type, name, pref, cnt) as (
                SELECT Nba.type, Preferences.nba_entity, Preferences.preference, COUNT(*) as cnt
                FROM Preferences, Users, Nba
                WHERE Preferences.user = Users.user
                AND Preferences.nba_entity = Nba.name
                GROUP BY Preferences.nba_entity, Preferences.preference
                ORDER BY cnt DESC
            )
            SELECT pref, type, cnt FROM fandom
            WHERE name = %s;
        """
        params = (nba_name,)
        title = f'{nba_name} Fandom Breakdown'
        columns = ['pref', 'type', 'cnt']
        
    if level and (not (nba_type and nba_name)):  # select for example all the 
        query = f"""
            WITH fandom (type, name, pref, cnt) as (
                SELECT Nba.type, Preferences.nba_entity, Preferences.preference, COUNT(*) as cnt
                FROM Preferences, Users, Nba
                WHERE Preferences.user = Users.user
                AND Preferences.nba_entity = Nba.name
                GROUP BY Preferences.nba_entity, Preferences.preference
                ORDER BY cnt DESC
            )
            SELECT name, cnt FROM fandom
            WHERE pref = %s;
        """
        params = (level)
        title = f'{level} Breakdown'
        columns = ['name', 'cnt']
    
    if (level and nba_type) and not nba_name: # select for example all bandwagoners of teams
        query = f"""
            WITH fandom (type, name, pref, cnt) as (
                SELECT Nba.type, Preferences.nba_entity, Preferences.preference, COUNT(*) as cnt
                FROM Preferences, Users, Nba
                WHERE Preferences.user = Users.user
                AND Preferences.nba_entity = Nba.name
                GROUP BY Preferences.nba_entity, Preferences.preference
                ORDER BY cnt DESC
            )
            SELECT name, cnt FROM fandom
            WHERE pref = %s
            AND type = %s;
        """
        params = (level, nba_type)
        title = f'{level} {nba_type} Breakdown'
        columns = ['name', 'cnt']
    
    combined_output = []
    
    for db in metadata['Connections']:
        
        output = dbm.query_one(query, metadata['Connections'][db], params=params)
        
        combined_output.extend(list(output))
    
    return columns, title, combined_output

def select_user(user):
    metadata = dbm.read_metadata()
    
    query = """
        SELECT Nba.type, Nba.name, Preferences.preference, Users.user, Users.date
        FROM Preferences, Users, Nba
        WHERE Preferences.user = Users.user
        AND Preferences.nba_entity = Nba.name
        AND Preferences.user = %s;
    """
    params = (user,)
    combined_output = []
    dbs = []
    for db in metadata['Connections']:
        output = dbm.query_one(query, metadata['Connections'][db], params=params)
        combined_output.append(output)
        dbs.append(db)
    return dbs, combined_output

    
def show_databases():
    metadata = dbm.read_metadata()
    
    dbs = {}
    capacities, _ = dbp.check_capacities()
    
    for db in metadata['Connections']:
        keys = db.split('r')[1].split('h')
        dbs[db] = {
            'range': keys[0],
            'end': metadata['Ranges']['End'][metadata['Ranges']['Start'].index(int(keys[0]))],
            'DB#': keys[1],
            'host': metadata['Connections'][db]['vm_ip'],
            'data_size': capacities[db],
            'db_capacity': '4000 MB'
        }
        
    dbs = pd.DataFrame(dbs).transpose().reset_index()
    
    return dbs

def init_dbs(num_dbs):
    dbp.initiate_distributed_db(num_dbs)
    
def destroy_dbs():
    dbp.destroy_distributed_db()
    
def show_metadata():
    return dbm.read_metadata()


def main():
    parser = init_parsers()
    args = parser.parse_args()
    
    if args.command == 'insert':
        if args.json:
            try:
                with open(args.json, 'r') as file:
                    data = json.load(file)
                    if isinstance(data, list):
                        insert(args.table, data)
                    else:
                        print('Make sure the json file is a list of objects.')
            except DuplicateDataError as e:
                print(e)
                print('Duplicate data error')

                
        elif args.data:
            insert(args.table, [json.loads(record) for record in args.data])
        else:
            print('cli.py insert: error: Pick either json or manual insertion')
    if args.command == 'delete':
        if args.database:
            if args.condition:
                delete(args.table, db=args.database, condition=args.condition)
            else:
                delete(args.table, db=args.database)
        else:
            if args.condition:
                delete(args.table, condition=args.condition)
            else:
                delete(args.table)
    if args.command == 'update':

        if args.database:
            
            update(args.table, args.set, condition=args.condition)
        else:
            update(args.table, args.set, condition=args.condition, db=args.database)

    if args.command == 'select':
        if args.table:
            starting = datetime.now()
            num_rows, res = select_all(args.table)
            ending = datetime.now()
            
            time = ending - starting
            
            print(res)
            print(f'Total rows: {num_rows} ({time.total_seconds():.2f} sec)')
        
        if args.nbaType:
            starting = datetime.now()
            num_rows, res = select_all(args.nbaType)
            ending = datetime.now()
            time = ending - starting
            print(res)
            print(f'Total rows: {num_rows} ({time.total_seconds():.2f} sec)')
        
    if args.command == 'breakdown':
        starting = datetime.now()
        cols, title, res = select_fandom(nba_name=args.name, nba_type=args.type, level=args.level)
        
        df = pd.DataFrame(res, columns=cols)
        result = df.groupby(cols[:-1]).agg({'cnt': 'sum'}).sort_values(by='cnt', ascending=False).reset_index()
        ending = datetime.now()
        time = ending - starting
        
                
        
        print('\n', title.title())
        print(tabulate(result, showindex=False, tablefmt='psql', headers=cols))
        print(f'{len(result)} rows in set ({time.total_seconds():.3f} sec)')

    if args.command == 'user':
        
        starting = datetime.now()
        dbs, res = select_user(args.user)
        ending = datetime.now()
        time = ending - starting
        
        print(f'{len([item for t in res for item in t])} total rows across DBs ({time.total_seconds():.3f} sec)')
        
        print(f'\nResults for user "{args.user}"\n')
        for i, user_instance in enumerate(res):
            print(f'Database {dbs[i]}:')
            print(tabulate(user_instance, headers=['type', 'name', 'fandom_level', 'user', 'date'], tablefmt='psql'), '\n')
    
    if args.command == 'metadata':
        if args.verbose:
            pprint(show_metadata())
            
        else:
            print(tabulate(show_databases(), tablefmt='psql', showindex=False, headers=['DB', 'Start', 'End', 'Hash Value', 'Host', 'DB Size', 'DB Capacity']))
            
    if args.command == 'init':
        init_dbs(args.dbs)
        
    if args.command == 'destroy':
        check = input(f'Are you sure you want to destroy the distributed database?\nTo confirm the destroy, type "destroy": ')
        
        if check == 'destroy':
            print('Destroying the distributed database.')
            print(tabulate(show_databases(), tablefmt='psql', showindex=False, headers=['DB', 'Start', 'End', 'Hash Value', 'Host', 'DB Size', 'DB Capacity']))
            destroy_dbs()
        
    if args.command == 'expand':
        check = input(f'Are you sure you want to add {args.num_dbs} more databases? (Y/n) ')
        if check == 'Y':
            print('Old Metadata')
            print(tabulate(show_databases(), tablefmt='psql', showindex=False, headers=['DB', 'Start', 'End', 'Hash Value', 'Host', 'DB Size', 'DB Capacity']))
            print(f'\nADDING {args.num_dbs} NEW DATABASES')
            dbp.add_databases(args.num_dbs)
            
    
            
if __name__ == '__main__':  
    main()


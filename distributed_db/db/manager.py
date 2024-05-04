from datetime import datetime
from pprint import pprint
import json
from typing import Optional
from time import sleep

import pymysql

try:
    from distributed_db.db.exceptions import DateOutOfRangeError, MetadataDateError, TerraformError, EmptyMetadataError, DuplicateDataError
except ModuleNotFoundError:
    from .exceptions import DateOutOfRangeError, MetadataDateError, TerraformError, EmptyMetadataError, DuplicateDataError

MODULUS = 2

class DatabaseManager():
    """
    Class for all operations available to be performed on data in the distributed database. Data is partitioned based on both the user's name and the date the account/post was created.
    
    Methods:
    \tlocate_db - Locates the database corresponding to the user's name and the date of account/post creation.\n
    \tretrieve_data - read/retrieve data from the distributed database\n
    \tcreate_data - create data and insert into database\n
    \tupdate_data - update data in the database\n
    \tdelete_data - delete data in the database\n
    
    """
    def __init__(self, metadata_path) -> None:
        self.metadata_path = metadata_path
        self.mysql_connection_params = {'port': 3306}
        self.mysql_tables = {
            'user': 'Users',
            'users': 'Users',
            'prefs': 'Preferences',
            'nba': 'Nba',
            'username': 'Users'
        }
        
    def set_database_params(self, credentials):
        self.mysql_connection_params['host'] = credentials['vm_ip']
        self.mysql_connection_params['user'] = credentials['mysql_username']
        self.mysql_connection_params['password'] = credentials['mysql_password']
        self.mysql_connection_params['database'] = credentials['mysql_database']
        
    def read_metadata(self) -> dict: 
        """
        Read the metadata.
        """
        with open(self.metadata_path, 'r') as file:
            metadata = json.load(file)
        return metadata
    
    def calculate_hash(self, user: str, modulus: int) -> int:
        """
        Calculates the hash of the user's name based on the modulus.\n
        
        Parameters:
        \tuser - the user's name to be hashed.\n
        \tmodulus - the modulus for hashing, equal to the number of databases in the user's range partition.\n
        
        Returns:
        \thash_value - the hash value of the user's name. 
        """
        
        hash_value = sum(ord(char) for char in user) % modulus
        
        return hash_value

    
    def locate_db(self, metadata: dict,  data_date: int, user_name: str) -> int:
        """
        Locate the index of the Metadata "Ranges" lists based on which range the data-origin-date falls in between.
        
        Parameters: 
        \tavailable_partitions - a zip of the Metadata "Ranges" lists ("Start", "End", and "Moduli" sorted arrays).\n
        
        Returns:
        \ttarget_range_index: the index of the partition metadata two which the data_date belongs.
        """
        
        available_partitions = list(
            zip(
                metadata["Ranges"]["Start"], 
                metadata["Ranges"]["End"], 
                metadata["Ranges"]["Moduli"]
            )
        )
        
        if not isinstance(data_date, int):
            raise ValueError(f"Date must be of type int - got type {type(data_date).__name__} instead.")

        now = datetime.now()
        today = int(now.strftime("%Y%m%d%H"))
        
        if data_date > today:
            raise DateOutOfRangeError("This date is in the future.", data_date)
        elif data_date < available_partitions[0][0]:
            raise DateOutOfRangeError("This date was prior to the initiation of the database system.", data_date)
        elif data_date > available_partitions[-1][0]:
            target_range_index = -1
        else:
            left = 0 
            right = len(available_partitions)
            while left <= right:
                mid = (right + left) // 2
                
                db_start_date = available_partitions[mid][0]
                db_end_date = available_partitions[mid][1] if available_partitions[mid][1] else today

                if data_date < db_start_date:
                    right = mid - 1
                elif data_date > db_end_date:
                    left = mid + 1
                else:
                    target_range_index = mid
                    # print(target_range_index)
                    break
        
        modulus = available_partitions[target_range_index][2]
        db_range_value = available_partitions[target_range_index][0]
        db_hash_value = self.calculate_hash(user=user_name, modulus=modulus) 
        
        db_name = f'r{db_range_value}h{db_hash_value}'
    
        return db_name
        
    def insert_one(self, data: dict, table: str, credentials: dict):
        """
        Insert one record into one database.
        """
        
        self.set_database_params(credentials)
        
        if table == 'users':
            
            query = """
                INSERT INTO Users(user, password, date)
                VALUES (%(user)s, %(password)s, %(date)s);
            """
        
            query_params = {
                'user': data['user'], 
                'password': data['password'], 
                'date': data['date']
            }
            
        elif table == 'prefs':
            query = """
                INSERT INTO Preferences(user, nba_entity, preference)
                VALUES (%(user)s, %(nba_entity)s, %(preference)s);
            """
        
            query_params = {
                'user': data['user'], 
                'nba_entity': data['nba_entity'], 
                'preference': data['preference']
            }
            
            
        elif table == 'nba':
            query = """
                INSERT INTO Nba(name, type)
                VALUES (%(name)s, %(type)s);
            """
        
            query_params = {
                'name': data['name'], 
                'type': data['type']
            }
        
        try:
            with pymysql.connect(**self.mysql_connection_params) as connection:
                with connection.cursor() as cursor:
                    rows = cursor.execute(query, query_params)
                    print(f'Query OK, {rows} rows affected -- DB {self.mysql_connection_params["database"]}')
                    connection.commit()
                    # return 1
        except pymysql.err.OperationalError as e:
            raise e
        except pymysql.err.IntegrityError as err:
            if err.args[0] == 1062:
                raise DuplicateDataError(err)
    
    
    
    def delete_from_one(self, table, credentials, condition: Optional[str] = None):
        
        self.set_database_params(credentials)
        mysql_table = self.mysql_tables[table]
        
        if not condition:
            delete_all = input(f'Are you sure you want to everything in {self.mysql_connection_params["database"]}.{mysql_table}? (Y/n): ')
            if delete_all == 'Y':
                query = f"""
                    DELETE FROM {mysql_table};  
                """   
        else:
            query = f"""
                    DELETE FROM {mysql_table}
                    WHERE {condition};  
                """
        with pymysql.connect(**self.mysql_connection_params) as connection:
                with connection.cursor() as cursor:
                    rows = cursor.execute(query)
                    print(f'Query OK, {rows} rows affected -- DB {self.mysql_connection_params["database"]}')
                    connection.commit()
                    
    def update_in_one(self, table, credentials, set_clause, condition: Optional[str] = None):
        
        self.set_database_params(credentials)
        
        mysql_table = self.mysql_tables[table]
        
        if condition:
        
            query = f"""
                    UPDATE {mysql_table} 
                    SET {set_clause} 
                    WHERE {condition};
            """
        else:
            query = f"""
                    UPDATE {mysql_table} 
                    SET {set_clause};
            """
        
        try:
            with pymysql.connect(**self.mysql_connection_params) as connection:
                with connection.cursor() as cursor:
                    rows = cursor.execute(query)
                    print(f'Query OK, {rows} rows affected -- DB {self.mysql_connection_params["database"]}')
                    connection.commit()
        except pymysql.err.IntegrityError as err:
            if err.args[0] == 1062:
                print('This update would create a duplicate row. Update aborted.')
                
                
    def query_one(self, query, credentials, params: Optional[tuple[str]] = None):
        self.set_database_params(credentials)

        with pymysql.connect(**self.mysql_connection_params) as connection:
            with connection.cursor() as cursor:
                if params:
                    rows = cursor.execute(query, params)
                else:
                    rows = cursor.execute(query)
                print(f'Query OK, {rows} rows affected -- DB {self.mysql_connection_params["database"]}')
                out = cursor.fetchall()
                
                return out
        
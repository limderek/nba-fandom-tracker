from datetime import datetime
from pprint import pprint
import subprocess
import json
import os
from typing import Union, Literal, Optional
from time import sleep

import pymysql

try:
    from distributed_db.db.exceptions import DateOutOfRangeError, MetadataDateError, TerraformError, EmptyMetadataError
    from distributed_db.db.constants import DEFAULT_MODULUS
except ModuleNotFoundError:
    from .exceptions import DateOutOfRangeError, MetadataDateError, TerraformError, EmptyMetadataError
    from .constants import DEFAULT_MODULUS


class DatabaseProvisioner():
    def __init__(self, metadata_path, terraform_dir) -> None:
        self._modulus = DEFAULT_MODULUS
        self.metadata_path = metadata_path
        self.TERRAFORM_DIR = terraform_dir
        self.instances = []
        self.capacities = {}
        self.__init_new_dbs = False
        self.__new_metadata = {}
        
    
        
    def update_modulus(self, new_modulus: int) -> None:
        self._modulus = new_modulus
    
    def read_metadata(self) -> dict:
        """
        Reads the metadata file and returns it as a dictionary
        """
        with open(self.metadata_path, 'r') as file:
            metadata = json.load(file)
        return metadata
    
    def __initiate_metadata(self, db_ips: dict, modulus: int) -> None:
        """
        works
        """
        
        now = datetime.now()
        start_range = int(now.strftime("%Y%m%d%H")) - 3
        
        metadata = self.read_metadata()
        
        metadata['Ranges']['Start'] = [start_range]
        metadata['Ranges']['End'] = [None]
        metadata['Ranges']['Moduli'] = [modulus]
        
        for db in db_ips:
            metadata['Connections'][db] = {
                "mysql_username": db,
                "mysql_password": db,
                "mysql_database": db,
                "vm_ip": db_ips[db]
            }
        with open(self.metadata_path, 'w') as file:
            json.dump(metadata, file, indent=4)
            
    def __mark_dbs_for_close(self) -> int:
        """
        works
        """
        now = datetime.now()
        prev_end_range = int(now.strftime("%Y%m%d%H"))
        next_range = prev_end_range + 1
        
        metadata = self.read_metadata()
        
        prev_end_range = metadata['Ranges']['Start']
        
        # print(metadata['Ranges']['Start'][-1])
        
        if metadata['Ranges']['Start'][-1] < prev_end_range:
            metadata['Ranges']['End'][-1] = prev_end_range
        elif metadata['Ranges']['Start'][-1] == prev_end_range: 
            msg = 'Database range erroneously created in the same hour the last one started'
            raise MetadataDateError(msg, prev_end_range)
        else:
            raise MetadataDateError("Invalid Date", prev_end_range)
        
        with open(self.metadata_path, 'w') as file:
            json.dump(metadata, file, indent=4)
        
        return next_range
    
    def update_metadata(self, new_db_ips: list) -> None:
        """
        works
        """
        
        try:
            next_range_start = self.__mark_dbs_for_close()
        except MetadataDateError:
            raise
        metadata = self.read_metadata()
        
        metadata['Ranges']['Start'].append(next_range_start)
        metadata['Ranges']['End'].append(None)
        metadata['Ranges']['Moduli'].append(self._modulus)
        
        db_dict = {}
        for i, d in enumerate(new_db_ips):
            db_dict[f'r{next_range_start}h{i}'] = d
        
        for db in db_dict:
            metadata['Connections'][db] = {
                "mysql_username": db,
                "mysql_password": db,
                "mysql_database": db,
                "vm_ip": db_dict[db]
            }
        
        with open(self.metadata_path, 'w') as file:
            json.dump(metadata, file, indent=4)
            
    
    def initiate_distributed_db(self, modulus: Optional[int] = None):
        """
        create the terraform variable map
        call python subprocess
        write metadata file
        """
        
        metadata = self.read_metadata()
        
        if metadata['Connections']:
            raise TerraformError('Distributed DB has already been initiated.')
        
        now = int(datetime.now().strftime("%Y%m%d%H")) - 3
        
        for h in range(int(modulus) if modulus else self._modulus):
            self.instances.append(f'r{now}h{h}')

        instances_map = {}
        
        for instance in self.instances:
            instances_map[instance] = {
                'mysql_username': instance,
                'mysql_password': instance,
                'mysql_database': instance
            }
        
        instances_map = json.dumps(instances_map)
        
        init_command = [
            'terraform',
            f'-chdir={self.TERRAFORM_DIR}',
            'init',
        ]
        
        apply_command = [
            'terraform',
            f'-chdir={self.TERRAFORM_DIR}',
            'apply',
            '-var',
            f'map_of_instance_data={instances_map}',
            '--auto-approve'
        ]
        
        outputs_command = [
            'terraform',
            f'-chdir={self.TERRAFORM_DIR}',
            'output',
            '-json'
        ]
        
        init_out = subprocess.run(init_command, capture_output=True)
        if init_out.returncode != 0:
            print(init_out.stderr.decode())
            raise TerraformError(f'Terraform Init Failed.\n{init_out.stderr.decode()}')
        else:
            print(init_out.stdout.decode()) # Print the output to the console
        
        apply_out = subprocess.run(apply_command, capture_output=True)
        if apply_out.returncode != 0:
            print(apply_out.stderr.decode())
            raise TerraformError(f'Terraform Apply Failed.\n{apply_out.stderr.decode()}')
        else:
            print(apply_out.stdout.decode()) # Print the output to the console

        output = subprocess.run(outputs_command, capture_output=True)
        
        db_ips = json.loads(output.stdout.decode())['public_ips']['value']
        
        self.__initiate_metadata(db_ips,  modulus if modulus else self.modulus)
        
    def retrieve_previous_session(self):
        metadata = self.read_metadata()
   
        if not metadata['Connections']:
            raise EmptyMetadataError('Please initiate the distributed database first.')
        
        for db in metadata['Connections']:
            self.instances.append(db)
            
        self._modulus = metadata['Ranges']['Moduli'][-1]
        
        return self.instances
        
        
    def clear_metadata(self) -> None:
        with open(self.metadata_path, 'r') as file:
            metadata = json.load(file)
            
        for v in metadata['Ranges']:
            metadata['Ranges'][v] = []
        
        metadata['Connections'] = {}
        
        with open(self.metadata_path, 'w') as file:
            json.dump(metadata, file, indent=4)
    
    def __get_instance_map(self) -> str:  ###
        
        instances_map = {}
        
        metadata = self.read_metadata()
            
            
        for instance in metadata['Connections']:
            instances_map[instance] = {
                'mysql_username': instance,
                'mysql_password': instance,
                'mysql_database': instance
            }
        
        instances_json = json.dumps(instances_map)

        return instances_json 
    
    def destroy_distributed_db(self) -> None:
        """
        call terraform destroy
        """
        instance_map = self.__get_instance_map()
        # instance_map = json.dumps({"r2024042816h0": {"mysql_username": "r2024042816h0", "mysql_password": "r2024042816h0", "mysql_database": "r2024042816h0"}, "r2024042815h0": {"mysql_username": "r2024042815h0", "mysql_password": "r2024042815h0", "mysql_database": "r2024042815h0"}, "r2024042815h1": {"mysql_username": "r2024042815h1", "mysql_password": "r2024042815h1", "mysql_database": "r2024042815h1"}})
        
        destroy_command = [
            'terraform',
            f'-chdir={self.TERRAFORM_DIR}',
            'destroy',
            '-var',
            f'map_of_instance_data={instance_map}',
            '--auto-approve'
        ]
        
        destroy_out = subprocess.run(destroy_command, capture_output=True)
        if destroy_out.returncode != 0:
            print(destroy_out.stderr.decode())
            raise TerraformError(f'Terraform Init Failed.\n{destroy_out.stderr.decode()}')
        else:
            print(destroy_out.stdout.decode()) # Print the output to the console
        self.clear_metadata()
    
    def stop_virtual_machines(self, vms: list = None) -> None: 
        pass
    
    def start_virtual_machines(self, vms: list = None) -> None:
        pass 
    
    def check_capacities(self):
        
        # current_instances = self.retrieve_previous_session()
        metadata = self.read_metadata()
        current_range = metadata['Ranges']['Start'][-1]
        
        capacities = {}
        near_full = []
        
        for db in metadata['Connections']:
            # if db in [f'r{current_range}h{h}' for h in range(metadata['Ranges']['Moduli'][-1])]:
            size = f"""select size 
            from (
                SELECT 
                    table_schema AS "Database", 
                    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS size 
                FROM 
                    information_schema.TABLES 
                GROUP BY 
                    table_schema
            ) s 
            where s.database = "{db}";"""
            
            host = metadata['Connections'][db]['vm_ip']
            
            with pymysql.Connection(host=host, user=db, database=db, password=db) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(size)
                    exists = cursor.fetchone()
                    capacities[db] = f'{exists[0]} MB'
                    if exists[0] > 3000:
                        near_full.append(host)
                        
        self.capacities = capacities            
        return capacities, near_full
    
    def __new_instance_map(self, new_instances: list = None):  ###
        instances_map = {}
        
        metadata = self.read_metadata()
            
            
        for instance in metadata['Connections']:
            instances_map[instance] = {
                'mysql_username': instance,
                'mysql_password': instance,
                'mysql_database': instance
            }
            
        if new_instances:
            for new_instance in new_instances:
                instances_map[new_instance] = {
                    'mysql_username': new_instance,
                    'mysql_password': new_instance,
                    'mysql_database': new_instance
                }
        
        instances_json = json.dumps(instances_map)
        
        pprint(instances_map)

        return instances_json 
    
    # @property
    # def init_new_range(self):
    #     return self.__init_new_dbs
    
    # @init_new_range.setter
    # def init_new_range(self, modulus):
    #     self.__init_new_dbs = modulus
    #     if modulus:
    #         self.add_databases(modulus)
 
    
    def add_databases(self, modulus: int): ###
        """
        if capacities over threshold (75%?): create new databases with new modulus
        """
        now = int(datetime.now().strftime("%Y%m%d%H"))
        
        
        metadata = self.read_metadata()
        current_range = metadata['Ranges']['Start'][-1]   
        metadata['Ranges']['End'][-1] = now - 1

        new_range = now
        new_dbs = [f'r{new_range}h{i}' for i in range(modulus)]
        
        
        instances_map = self.__new_instance_map(new_instances=new_dbs)
        
        init_command = [
            'terraform',
            f'-chdir={self.TERRAFORM_DIR}',
            'init',
        ]
        
        apply_command = [
            'terraform',
            f'-chdir={self.TERRAFORM_DIR}',
            'apply',
            '-var',
            f'map_of_instance_data={instances_map}',
            '--auto-approve'
        ]
        
        outputs_command = [
            'terraform',
            f'-chdir={self.TERRAFORM_DIR}',
            'output',
            '-json'
        ]
        
        init_out = subprocess.run(init_command, capture_output=True)
        if init_out.returncode != 0:
            print(init_out.stderr.decode())
            raise TerraformError(f'Terraform Init Failed.\n{init_out.stderr.decode()}')
        else:
            print(init_out.stdout.decode()) # Print the output to the console
        
        apply_out = subprocess.run(apply_command, capture_output=True)
        if apply_out.returncode != 0:
            print(apply_out.stderr.decode())
            raise TerraformError(f'Terraform Apply Failed.\n{apply_out.stderr.decode()}')
        else:
            print(apply_out.stdout.decode()) # Print the output to the console

        output = subprocess.run(outputs_command, capture_output=True)
        
        db_ips = json.loads(output.stdout.decode())['public_ips']['value']
        

        self.__init_new_dbs = False
        

        metadata['Ranges']['Start'].append(new_range)
        metadata['Ranges']['End'].append(None)
        metadata['Ranges']['Moduli'].append(modulus)

        for db in new_dbs:
            metadata['Connections'][db] = {
                "mysql_username": db,
                "mysql_password": db,
                "mysql_database": db,
                "vm_ip": db_ips[db]
            }
        
        with open(self.metadata_path, 'w') as file:
            json.dump(metadata, file, indent=4)
        


def main() -> None:
    dbp = DatabaseProvisioner(metadata_path='./metadata.json')
    
    
if __name__ == '__main__':
    main()
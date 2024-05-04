# NBA Fandom Tracker

## 0a. App Description
This app is a tracker that allows users to see data on their NBA teams/players of choice. These are chosen according to three different levels of fandom: fan, bandwagon, and rival. As the main sports apps do not acknowledge this functionality, this app is meant to allow users to further track their nba fandom preferences into better detail.

## 0b. Project Files
```bash
.
└── NBA-Fandom-Tracker/
    ├── distributed_db/
    │   ├── db/
    │   │   ├── terraform/
    │   │   │   ├── scripts/
    │   │   │   │   └── init_mysql.sh
    │   │   │   ├── main.tf
    │   │   │   ├── outputs.tf
    │   │   │   └── variables.tf
    │   │   ├── __init__.py
    │   │   ├── constants.py
    │   │   ├── exceptions.py
    │   │   ├── manager.py
    │   │   ├── provisioner.py
    │   │   └── metadata/
    │   │       ├── metadata_local.json
    │   │       ├── metadata_azure.json
    │   │       └── metadata_backup.json
    │   ├── api.py
    │   ├── cli.py
    │   ├── constants.py
    │   └── sample_data/
    │       ├── sample_nba.json
    │       ├── sample_prefs.json
    │       └── sample_users.json
    ├── web_ui/
    │   └── app.py
    ├── README.md
    ├── .gitignore
    ├── requirements.txt
    └── setup_db.txt
    └── demo.txt
```
## 0c. Description of Files
- web_ui/ : directory for frontend user interface
    - **app.py**: Streamlit app for the frontend user interface. Makes requests to the Flask app. Entrypoint for Web-UI.
- distributed_db/ : directory for the code interacting with the distributed database
    - **api.py**: Flask app to handle requests from the Streamlit app to the distributed database.
    - **cli.py**: Command line interface for database manager. Entrypoint for DBMS-UI.
    - db/ : package for internal infrastructure, database, and partitioning logic 
        - manager.py: code for querying and partitioning of data. Called by api.py and cli.py for database management.
        - provisioner.py: code for provisioning Azure Virtual Machines and MySQL databases. Called by cli.py for infrastructure management.
        - terraform/ : directory for Terraform code and state files. Runs via a Python subprocess by provisioner.py (terraform init, apply, destroy).
            - main.tf: Terraform code for provisioning the Azure infrastructure, including resource group, security group, subnet, security group, security rule, virtual network, public ip, network interface, and the virtual machines themselves.
            - variables.tf: Terraform variable definitions. 
            - outputs.tf: Terraform output definitions.
            - scripts/init_mysql.sh: shell script for installing MySQL, setting up database/user/password, permissions, and creating tables. This script is passed as Azure custom data to each newly provisioned Azure VM in order to immediately set up MySQL with the proper permissions and tables as soon as each Azure VM is up and running.
        - metadata/ : contains JSON metadata files tracking partition metadata and database connection credentials
        - constants.py: constants used by manager.py and provisioner.py. Mainly for testing purposes.
        - exceptions.py: custom exception classes for manager.py and provisioner.py
    - sample_data/ : contains JSON files with sample data for each of the tables in the database.
    - constants.py: constants used by cli.py and api.py. 
- setup_db.txt: instructions to setup MySQL databases, tables, and app metadata on local machine.
- demo.txt: sample commands for the DB manager CLI (same used in in-class project demo)

## 1a. Cloud-based Setup
- Install Terraform (3.96.0+)
    - https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli
- Microsoft Azure CLI
    - set Azure credentials (env variables)
    - https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/guides/azure_cli
- Install Python 3.11.1, or create a Python 3.11.1 venv
    - `python3 -m venv env`
    - `source env/bin/activate`
    - `pip install -r requirements.txt`
- Alter metadata filepath  constants in `./distributed_db/constants.py`, and the top of the files of `./distributed_db/cli.py` and `./distributed_db/api.py` to point to the appropriate metadata file.

## 1b. Local Setup
- Install Python 3.11.1, or create a Python 3.11.1 venv
    - `python3 -m venv env`
    - `source env/bin/activate`
    - `pip install -r requirements.txt`
- Alter metadata filepath constants in `./distributed_db/constants.py`, and the top of the files of `./distributed_db/cli.py` and `./distributed_db/api.py` to point to the appropriate metadata file.
- Install MySQL
- Follow MySQL setup instructions at `.distributed_db/setup_db.txt`
- NOTE: this version of the distributed database does not scale out. For options to add databases, refer to the previous section (1a).

## 2. Run Streamlit App
- in a separate terminal:
    - `cd web_ui`
    - `streamlit run app.py`

## 3. Run Flask App
- in a separate terminal:
    - `cd distributed_db`
    - `python3 api.py`

## 4. Run CLI Commands (examples in ./demo.txt)
- in a separate terminal:
    - `cd distributed_db`
- run commands:
    - initialize distributed database (cloud setup only): `python3 cli.py init <num_buckets>`
    - insert data:`python3 cli.py insert <table> [-j] <json filepath> [-d] <manual input>`
    - update data: `python cli.py update <table> <set> <condition> [-d] <database>`
    - select/read data from a table: `python cli.py select [-t] <table> [-n] <'team' | 'player'>`
    - read specific user data:`python3 cli.py user <username>`
    - read aggregate data:`python cli.py breakdown [--type] <type>  [--level] <level> [--name] <name>`
    - delete data:`python3 cli.py delete <table> [-d] <database> [-c] <condition>`
    - show metadata:`python3 cli.py metadata`
    - add databases (cloud setup only):`python3 cli.py expand <num_dbs>`
    - destroy entire database (cloud setup only):`python3 cli.py destroy`

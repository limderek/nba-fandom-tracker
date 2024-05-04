from pprint import pprint
from flask import Flask, jsonify, request
import pymysql
from db.manager import DatabaseManager
from constants import METADATA_LOCAL, AZURE_METADATA_PATH, METADATA_COPY

md = METADATA_LOCAL

app = Flask(__name__)
try:
    dbm = DatabaseManager(md)
    
except FileNotFoundError:
    dbm = DatabaseManager('/Users/charlottekho/Documents/GIT/DSCI-551-Project/distributed_db/db/metadata.json')
metadata = dbm.read_metadata()

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    date = data.get('date')
    db_key = dbm.locate_db(metadata, int(date), username)
    credentials = metadata['Connections'][db_key]

    connection = get_connection(credentials)
    try:
        with connection.cursor() as cursor:
            # Check if the user already exists
            sql_check = "SELECT * FROM Users WHERE user = %s"
            cursor.execute(sql_check, (username,))
            exists = cursor.fetchone()
            
            if exists:
                # Update the existing user
                sql_update = "UPDATE Users SET date = %s, password = %s WHERE user = %s"
                cursor.execute(sql_update, (date, password, username))
            else:
                # Insert new user
                sql_insert = "INSERT INTO Users (user, password, date) VALUES (%s, %s, %s)"
                cursor.execute(sql_insert, (username, password, date))
            
            connection.commit()
            return jsonify({"message": "Login successful", "username": username, "timestamp": date}), 200
    finally:
        connection.close()

@app.route('/api/save_preferences', methods=['POST'])
def save_preferences():
    data = request.get_json()
    print(data)
    username = data['username']
    timestamp = data['timestamp']

    db_key = dbm.locate_db(metadata, int(timestamp), username)
    credentials = metadata['Connections'][db_key]
    connection = get_connection(credentials)

    try:
        with connection.cursor() as cursor:
            # Create a mapping for the incoming data to database labels
            category_mapping = {
                'favorite_teams': 'favorite',
                'bandwagon_teams': 'bandwagon',
                'rival_teams': 'rival', 
                'favorite_players': 'favorite'
            }
            
            # Retrieve existing preferences to identify changes needed
            existing_preferences = {
                'favorite_teams': set(),
                'bandwagon_teams': set(),
                'rival_teams': set(), 
                'favorite_players': set()
            }

            cursor.execute("SELECT nba_entity, type, preference FROM Preferences, Nba WHERE Nba.name = Preferences.nba_entity AND user = %s", (username,))


            for row in cursor:
                existing_preferences[f"{row['preference']}_{row['type']}s"].add(row['nba_entity'])
            
            if not existing_preferences:
                for category in data.keys():
                    if category in category_mapping:
                        sql_nba = """
                                 INSERT INTO Nba (name, type)
                                 VALUES (%s, %s)
                             """
                        sql_preferences = """
                                INSERT INTO Preferences (user, nba_entity, preference)
                                VALUES (%s, %s, %s);
                        """
                        for item in data[category]:
                            cursor.execute(sql_nba, (item, 'team' if 'teams' in category else 'player'))
                            
                            cursor.execute(sql_preferences, (username, item, category_mapping[category]))
                        connection.commit()
            else:
                
                # create a list of new preferences that reflect the current state of the streamlit app
                new_preferences = {}
                
                for category in data.keys():
                    if category in category_mapping:
                        new_preferences[category] = set(data[category])
                
                for p in new_preferences:

                    # get items to delete
                    to_delete = existing_preferences[p].difference(new_preferences[p].intersection(existing_preferences[p]))
                    
                    # get items to add
                    to_add = new_preferences[p].difference(existing_preferences[p])

                    for item in to_add:
                        sql_nba = """
                                 INSERT INTO Nba (name, type)
                                 VALUES (%s, %s)
                        """
                        sql_preferences = """
                                INSERT INTO Preferences (user, nba_entity, preference)
                                VALUES (%s, %s, %s);
                        """
                        
                        try:
                            cursor.execute(sql_nba, (item, 'player' if p == 'favorite_players' else 'team'))
                               
                            
                            
                        except pymysql.err.IntegrityError as err:
                            if err.args[0] == 1062:
                                pass
                        try:                       
                            cursor.execute(sql_preferences, (username, item, category_mapping[p]))
                        except pymysql.err as err:
                            print(err)
                         
                            
                    for item in to_delete:
                        delete_stmt = """
                            DELETE FROM Preferences
                            WHERE user = %s 
                            AND nba_entity = %s 
                            AND preference = %s;
                        """
                        cursor.execute(delete_stmt, (username, item, category_mapping[p]))
                        connection.commit()   
                        
                connection.commit()
                    
            return jsonify({"message": "Preferences saved successfully"}), 200
    except Exception as e:
        print(e)
        connection.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()


@app.route('/api/delete_preferences', methods=['POST'])
def delete_preferences():
    data = request.get_json()
    username = data.get('username')
    timestamp = data.get('timestamp')

    if not username:
        return jsonify({"error": "Missing username"}), 400

    # Get database credentials
    db_key = dbm.locate_db(metadata, int(timestamp), username)
    credentials = metadata['Connections'][db_key]
    connection = get_connection(credentials)

    try:
        with connection.cursor() as cursor:
            # Delete all preferences for the user
            sql_delete = "DELETE FROM Preferences WHERE user = %s"
            cursor.execute(sql_delete, (username,))
            connection.commit()
            return jsonify({"message": "Preferences deleted successfully"}), 200
    except Exception as e:
        connection.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()


@app.route('/api/preferences/<username>', methods=['GET'])
def get_preferences(username):
    timestamp = request.args.get('timestamp', '')
    db_key = dbm.locate_db(metadata, int(timestamp), username)
    credentials = metadata['Connections'][db_key]
    connection = get_connection(credentials)

    try:
        with connection.cursor() as cursor:
            sql_query = """
            SELECT nba.name, nba.type, pref.preference
            FROM Preferences pref
            JOIN Nba nba ON nba.name = pref.nba_entity
            WHERE pref.user = %s
            """
            cursor.execute(sql_query, (username,))
            results = cursor.fetchall()

            print("Debug: Fetched preferences:", results)



            preferences = {
                "favorite_teams": [],
                "bandwagon_teams": [],
                "rival": [],
                "favorite_players": []
            }
            for row in results:
                if row['type'] == 'team':
                    if row['preference'] == 'favorite':
                        preferences['favorite_teams'].append(row['name'])
                    elif row['preference'] == 'bandwagon':
                        preferences['bandwagon_teams'].append(row['name'])
                    elif row['preference'] == 'rival':
                        preferences['rival'].append(row['name'])
                elif row['type'] == 'player':
                    if row['preference'] == 'favorite':
                        preferences['favorite_players'].append(row['name'])

                
            print(preferences)
            
            return jsonify(preferences), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()


# @app.route('/api/shared_preferences/<username>', methods=['GET'])
# def shared_preferences(username):
#     timestamp = request.args.get('timestamp', '')
#     db_key = dbm.locate_db(metadata, int(timestamp), username)
#     credentials = metadata['Connections'][db_key]
#     connection = get_connection(credentials)
#     try:
#         with connection.cursor() as cursor:
#             # Query for getting the preference counts by type (favorite, bandwagon, etc.) and entity
#             sql_query = """
#             SELECT nba.type, pref.preference, nba.name, COUNT(*) AS count
#             FROM Preferences pref
#             JOIN Users u ON u.user = pref.user
#             JOIN Nba nba ON nba.name = pref.nba_entity
#             WHERE pref.user <> %s AND pref.nba_entity IN (
#                 SELECT nba_entity
#                 FROM Preferences
#                 WHERE user = %s
#             ) AND pref.preference IN (
#                 SELECT preference
#                 FROM Preferences
#                 WHERE user = %s
#             )
#             GROUP BY nba.type, pref.preference, nba.name
#             """
#             cursor.execute(sql_query, (username, username, username))
#             results = cursor.fetchall()

#             # Organize results into a structured format
#             shared_prefs = {}
#             for result in results:
#                 key = f"{result['preference']}_{result['type']}_{result['name']}"
#                 shared_prefs[key] = result['count']

#             return jsonify(shared_prefs), 200
#     except Exception as e:
#         print(f"Database error: {str(e)}")
#         return jsonify({"error": str(e)}), 500
#     finally:
#         connection.close()




def get_connection(credentials):
    return pymysql.connect(
        host=credentials['vm_ip'],
        user=credentials['mysql_username'],
        password=credentials['mysql_password'],
        db=credentials['mysql_database'],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )






if __name__ == '__main__':
    app.run(debug=True)

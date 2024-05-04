#!/bin/bash

export user=${MYSQL_USERNAME}
export password=${MYSQL_PASSWORD}
export database=${MYSQL_DATABASE}

sudo apt update
sudo apt install mysql-server -y

sudo sed -i 's/.*bind-address.*/bind-address = 0.0.0.0/' /etc/mysql/mysql.conf.d/mysqld.cnf
sudo service mysql stop
sudo service mysql start

sudo mysql -e "CREATE USER '$user'@'%' IDENTIFIED WITH caching_sha2_password BY '$password';"
sudo mysql -e "FLUSH PRIVILEGES;"

sudo mysql -e "CREATE DATABASE $database;"
sudo mysql -e "GRANT ALL PRIVILEGES ON $database.* TO '$user'@'%';"
sudo mysql -e "GRANT SELECT ON information_schema.* TO '$user'@'%';"
sudo mysql -e "FLUSH PRIVILEGES;"

sudo cat > ~/db.sql <<-EOF
USE $database;

CREATE TABLE Users(
    user VARCHAR(32) NOT NULL,
    password VARCHAR(32) NOT NULL,
    date INT NOT NULL,
    PRIMARY KEY (user)
);

CREATE TABLE Nba(
    name VARCHAR(32) NOT NULL,
    type VARCHAR(16) NOT NULL,
    PRIMARY KEY (name)
);

CREATE TABLE Preferences(
    user VARCHAR(32) NOT NULL,
    nba_entity VARCHAR(32) NOT NULL,
    preference VARCHAR(16) NOT NULL,
    PRIMARY KEY (user, nba_entity, preference),
    FOREIGN KEY (user)
        REFERENCES Users(user)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    FOREIGN KEY (nba_entity)
        REFERENCES Nba(name)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);
EOF

sudo mysql -e "USE $database; SOURCE ~/db.sql;"
sudo rm ~/db.sql
import sqlparse
from pymysql import Connection
from pymysql.cursors import DictCursor
import pymysql
import re
from llama_index.llms.bedrock import Bedrock
from sqlglot import parse_one, errors
import random
import streamlit as st
import time


def get_connection(database: str = None, autocommit: bool = True) -> Connection:
    """
    Function that returns connection object to AWS RDS instance.
    :param: autocommit
    :return: pymysql connection
    """
    db_conf = {
        "host": st.secrets["aws_rds_host"],
        "port": 3306,
        "user": "admin",
        "password": st.secrets["aws_rds_password"],
        "autocommit": autocommit,
        "cursorclass": DictCursor,
        "client_flag": pymysql.constants.CLIENT.MULTI_STATEMENTS,  # Enable multi-statement mode
    }

    if database:
        db_conf["database"] = database

    try:
        connection = pymysql.connect(**db_conf)
        return connection

    except pymysql.MySQLError as e:
        print(f"Error connecting to the database: {e}")


def run_queries_in_schema(schema_name: str, query_list: list):
    """
    Function to execute queries within a specific schema in RDS instance.
    :param schema_name: Name of the schema to use
    :param query_list: List of SQL queries to execute
    """
    with get_connection(database=schema_name) as conn:
        with conn.cursor() as cursor:
            for query in query_list:
                cursor.execute(query)


def is_valid_query(query: str) -> bool:
    """
    Checks if the SQL query is a valid SELECT statement.
    :param: query (str): The SQL query to check.
    :return: boolean
    """
    parsed = sqlparse.parse(query)

    # Check if there's only one statement
    if len(parsed) != 1:
        return False

    # Get the first token of the statement
    first_token = parsed[0].tokens[0]

    # Check if the first token is a DML keyword and it's SELECT
    if first_token.ttype == sqlparse.tokens.DML and first_token.value.upper() == 'SELECT':
        return True
    else:
        return False


# Function to check if the SQL query is destructive
def is_non_destructive(sql_query: str) -> bool:
    """
    Check if the SQL query is non-destructive (i.e., does not contain DROP, DELETE, or TRUNCATE commands).
    :param: sql_query
    :return: boolean
    """
    destructive_keywords = ['DROP', 'DELETE', 'TRUNCATE']
    for keyword in destructive_keywords:
        # Check if the keyword exists in the query, ignoring case
        if re.search(rf'\b{keyword}\b', sql_query, re.IGNORECASE):
            print(f"Destructive query detected: {keyword} command found.")
            return False
    return True


# Function to validate SQL syntax using sqlglot
def is_valid_sql(sql_query: str) -> bool:
    """
    Check if the SQL query is valid using sqlglot.
    :param sql_query:
    :return: boolean
    """
    try:
        parse_one(sql_query)
        return True
    except errors.ParseError as e:
        print(f"Invalid SQL: {e}")
        return False


def clean_string(input_string: str) -> str:
    """
    Clean the input string by removing unnecessary characters.
    :param input_string:
    :return: cleaned string
    """

    cleaned_string = input_string.replace('```json', '')
    cleaned_string = cleaned_string.replace("\\'", "")
    cleaned_string = cleaned_string.replace('\n', '')
    cleaned_string = cleaned_string.strip()

    return cleaned_string


def initiate_llm():
    """
    Function to initiate the Claude 3.5 Sonnet model from Bedrock.
    :return: Bedrock model object
    """
    llm = Bedrock(
        model="anthropic.claude-3-5-sonnet-20240620-v1:0",
        aws_access_key_id=st.secrets["aws_access_key"],
        aws_secret_access_key=st.secrets["aws_secret"],
        region_name="eu-central-1",
        temperature=1,
        max_tokens=8192,
    )
    return llm


def create_schema_and_tables(schema_name: str):
    """
    Function to create a schema and tables in TiDB cluster.
    :param schema_name: Name of the schema to create
    """
    create_table_victim = f"""
    USE {schema_name};
    CREATE TABLE Victim (
        victim_id INT NOT NULL,
        name VARCHAR(100),
        age INT,
        occupation VARCHAR(100),
        time_of_death DATETIME,
        location_of_death VARCHAR(100),
        PRIMARY KEY (victim_id)
    );
    """

    create_table_suspects = f"""
    USE {schema_name};
    CREATE TABLE Suspects (
        suspect_id INT NOT NULL,
        name VARCHAR(100),
        age INT,
        relationship_to_victim VARCHAR(100),
        motive VARCHAR(100),
        PRIMARY KEY (suspect_id)
    );
    """

    create_table_alibis = f"""
    USE {schema_name};
    CREATE TABLE Alibis (
        alibi_id INT NOT NULL,
        suspect_id INT,
        alibi VARCHAR(255),
        alibi_verified BOOLEAN,
        alibi_time DATETIME,
        PRIMARY KEY (alibi_id),
        FOREIGN KEY (suspect_id) REFERENCES Suspects(suspect_id)
    );
    """

    create_table_crime_scene = f"""
    USE {schema_name};
    CREATE TABLE CrimeScene (
        scene_id INT NOT NULL,
        location VARCHAR(100),
        description TEXT,
        evidence_found BOOLEAN,
        victim_id INT,
        PRIMARY KEY (scene_id),
        FOREIGN KEY (victim_id) REFERENCES Victim(victim_id)
    );
    """

    create_table_evidence = f"""
    USE {schema_name};
    CREATE TABLE Evidence (
        evidence_id INT NOT NULL,
        description TEXT,
        found_at_location VARCHAR(100),
        points_to_suspect_id INT,
        scene_id INT,
        PRIMARY KEY (evidence_id),
        FOREIGN KEY (points_to_suspect_id) REFERENCES Suspects(suspect_id),
        FOREIGN KEY (scene_id) REFERENCES CrimeScene(scene_id)
    );
    """

    create_table_murderer = f"""
    USE {schema_name};
    CREATE TABLE Murderer (
        murderer_id INT NOT NULL,
        suspect_id INT,
        name VARCHAR(100),
        PRIMARY KEY (murderer_id),
        FOREIGN KEY (suspect_id) REFERENCES Suspects(suspect_id)
    );
    """

    table_queries = [
        create_table_victim,
        create_table_suspects,
        create_table_alibis,
        create_table_crime_scene,
        create_table_evidence,
        create_table_murderer
    ]

    # Step 1: Connect without specifying a database to create the user schema
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE SCHEMA {schema_name};")

            # run create table queries
            for query in table_queries:
                cursor.execute(query)


def generate_username() -> str:
    """
    Function to generate random username for leaderboard.
    :return: username str
    """
    adjectives = [
        "Wacky", "Silly", "Cheerful", "Quirky", "Funky", "Zany", "Bubbly",
        "Gigantic", "Mischievous", "Goofy", "Bouncy", "Sneaky", "Jolly"
    ]

    animals = [
        "Panda", "Kangaroo", "Penguin", "Platypus", "Llama", "Elephant",
        "Giraffe", "Dolphin", "Sloth", "Otter", "Chameleon", "Hedgehog", "Moose"
    ]

    # Generate a random username by combining an adjective, an animal, and a random number
    adjective = random.choice(adjectives)
    animal = random.choice(animals)
    number = random.randint(1000, 9999)

    # Combine them into a username
    username = f"{adjective}{animal}{number}"

    return username

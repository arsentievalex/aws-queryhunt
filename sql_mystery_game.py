import streamlit as st
import pymysql
from streamlit_ace import st_ace
from utils.utils import get_connection, is_valid_query, initiate_llm, create_schema_and_tables, generate_username, run_queries_in_schema
import pandas as pd
from utils.workflow import run_workflow
import asyncio
import time
from datetime import datetime
import streamlit.components.v1 as components
from pymysql.err import ProgrammingError
import re


@st.fragment
def show_hint(hint_prompt):
    """
        Displays a "Get Hint" button and generates a hint using an LLM when clicked.

        Args:
            hint_prompt (str): A template string for the LLM input with placeholders for
                `story`, `queries`, and `hints` from the session state.

        Session State:
            - `ai_story` (str): The AI-generated story.
            - `user_queries` (list): User-submitted queries.
            - `ai_hints` (list): Previously generated hints.

        Returns:
            None
    """
    hint_button = st.button('Get Hint 🪄')

    if hint_button and st.session_state.ai_story is not None:
        with st.spinner("Thinking..."):
            llm = initiate_llm()
            response = llm.stream_complete(hint_prompt.format(story=st.session_state.ai_story,
                                                             queries=st.session_state.user_queries,
                                                             hints=st.session_state.ai_hints))
        # Stream
        placeholder = st.empty()
        full_hint = ""
        for chunk in response:
            full_hint += chunk.delta
            placeholder.markdown(full_hint)

        # add to session state
        st.session_state['ai_hints'].append(full_hint)


@st.fragment
def check_solution():
    """
        Checks the user's solution to the mystery against the correct answer.

        Prompts the user to input their guess for the murderer's name, compares it to the correct solution
        retrieved from the database, and updates the session state accordingly.

        Session State:
            - `ai_story` (str): The AI-generated story (must not be None to proceed).
            - `user_solutions` (list): A list of guesses submitted by the user.
            - `current_user` (str): The current user's database schema for querying.
            - `start_time` (float): The start time of the game.
            - `end_time` (float): The end time of the game, set if the solution is correct.
            - `elapsed_time` (float): The total time taken to solve the mystery, calculated on success.

        Behavior:
            - If the user's solution matches the correct answer, the game ends, elapsed time is calculated,
              and a success animation is displayed.
            - If the user's solution is incorrect, a warning message prompts them to try again.

        Returns:
            None
    """
    user_solution = st.text_input("Who's the murderer?", label_visibility='collapsed',
                                  placeholder="Who's the murderer? Insert full name")

    if user_solution and st.session_state.ai_story is not None:

        # add to session state
        st.session_state.user_solutions.append(user_solution)

        # get correct solution
        with get_connection(autocommit=True, database=st.session_state.current_user) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT name from Murderer;")
                data = cursor.fetchall()
                solution = data[0]['name']

        # compare correct solution with user solution
        if user_solution.strip() == solution.strip():
            # record end time
            st.session_state.end_time = time.time()
            st.session_state.elapsed_time = st.session_state.end_time - st.session_state.start_time

            st.balloons()

            # show dialog window
            end_game()
        else:
            st.warning("Not exactly...try again!")


@st.fragment
def sql_editor():
    """
        Provides a SQL editor for users to input and execute queries, displaying the results in a table.

        The function uses an ACE editor for SQL input and validates the query syntax.
        If valid, the query is executed against the database associated with the current user,
        and the results are displayed as a dataframe.

        Session State:
            - `ai_story` (str): The AI-generated story (must not be None to proceed).
            - `current_user` (str): The current user's database schema for query execution.

        Behavior:
            - Displays an ACE SQL editor with syntax highlighting and various customization options.
            - Validates the SQL query and ensures it is a SELECT statement.
            - Executes the query if valid and displays the results in a Streamlit dataframe.
            - Displays an error message for invalid syntax or database execution errors.

        Returns:
            None
    """
    sql_query = st_ace(
        placeholder="Your SQL query here...",
        language="sql",
        theme="tomorrow_night",
        keybinding="vscode",
        font_size=15,
        show_gutter=False,
        show_print_margin=False,
        wrap=False,
        auto_update=False,
        min_lines=10,
        key="ace",
    )

    if sql_query and st.session_state.ai_story is not None:
        if not is_valid_query(sql_query):
            st.error("Wrong query syntax or non-Select statement. Please provide a valid SQL query.")
        else:
            try:
                with get_connection(autocommit=True, database=st.session_state.current_user) as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(sql_query)
                        data = cursor.fetchall()

                        column_names = [desc[0] for desc in cursor.description]
                        df = pd.DataFrame(data, columns=column_names)

                        # display the result as df
                        st.dataframe(df, hide_index=True, use_container_width=True)
            except pymysql.Error as e:
                st.error(e)


@st.dialog("Woo hoo!")
def end_game():
    """
        Ends the QueryHunt game by displaying the completion message, sharing option, and recording the result.

        The function calculates the total elapsed time, displays a congratulatory message, and provides an X
        sharing button. It also appends the player's result to the leaderboard and cleans up by dropping the
        temporary database schema.

        Session State:
            - `elapsed_time` (float): The total time taken by the user to solve the game (in seconds).

        Behavior:
            - Formats and displays the elapsed time in minutes and seconds.
            - Provides a Twitter share button pre-filled with the user's time.
            - Records the result by calling `add_to_leaderboard()`.
            - Cleans up the temporary database schema by calling `drop_temp_schema()`.

        Returns:
            None
    """

    minutes = int(st.session_state.elapsed_time // 60)
    seconds = int(st.session_state.elapsed_time % 60)

    st.markdown(f"""
        Great job! You correctly identified the murderer and solved the QueryHunt game in 
        <span style="color:#4CAF50; font-weight:bold;">{minutes}:{seconds:02d}</span> min!
    """, unsafe_allow_html=True)

    components.html(
        f"""<a class="twitter-share-button" href="https://twitter.com/intent/tweet" data-text="I solved the QueryHunt game in {minutes}:{seconds:02d} min. What is your time? 🧐"  data-url="https://queryhunt-game.streamlit.app/" data-hashtags="SQLMurderMystery">
    <script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script></a>
    """, width=100, height=30)

    # append result to TiDB table
    add_to_leaderboard()

    # drop schema
    drop_temp_schema()


def add_to_leaderboard():
    """
        Adds the user's game result to the leaderboard.

        Generates a random username and records the current date and the total elapsed time in the
        `Leaderboard` table of the database.

        Session State:
            - `elapsed_time` (float): The total time taken by the user to complete the game (in seconds).

        Returns:
            None
    """
    # Get today's date
    today_date = datetime.today().strftime('%Y-%m-%d')

    query = """
    INSERT INTO leaderboard (username, date, time_sec) 
    VALUES (%s, %s, %s);
    """

    random_username = generate_username()
    values = (random_username, today_date, int(st.session_state.elapsed_time))

    with get_connection(autocommit=True, database="original_game_schema") as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, values)


def drop_temp_schema():
    """
        Drops the temporary database schema associated with the current user.

        Safely constructs and executes a SQL query to remove the schema if it exists.

        Session State:
            - `current_user` (str): The name of the schema to be dropped.

        Returns:
            None
    """
    # Get the current user's schema name
    schema_name = st.session_state.current_user
    
    if schema_name:
        # Drop the temp schema by safely constructing the query
        query = f"DROP SCHEMA IF EXISTS `{schema_name}`;"
        
        with get_connection(autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)


def get_current_user():
    """
        Retrieves and sets the current user token in the session state.

        Extracts the user token from the request headers and assigns it to
        `st.session_state.current_user` if it is not already set.

        Session State:
            - `current_user` (str or None): The token representing the current user.

        Returns:
            None
    """
    #user_token = st.context.headers["X-Streamlit-User"]
    user_token = 'test_user'
    
    if st.session_state.current_user is None:
        st.session_state.current_user = user_token


HINT_PROMPT = """
You're an assistant helping a user with SQL murder mystery game.
Your goal is to provide a useful hint to a user and point them in the right direction towards identifying the correct murderer in the game.
Use your knowledge of dbml game schema.
Do not reveal the murderer.
Keep the hint short.

In your hint, reference the game story:
---------------------
{story}
---------------------
Here are the user's SQL queries so far:
---------------------
{queries}
---------------------
Here are your previous hints:
---------------------
{hints}
---------------------
"""

# for resetting temp db
delete_queries = [
    "DELETE FROM Evidence;",
    "DELETE FROM Murderer;",
    "DELETE FROM Alibis;",
    "DELETE FROM CrimeScene;",
    "DELETE FROM Suspects;",
    "DELETE FROM Victim;"
]

# initiate session state dicts
if "user_queries" not in st.session_state:
    st.session_state.user_queries = []
if "ai_hints" not in st.session_state:
    st.session_state.ai_hints = []
if "ai_story" not in st.session_state:
    st.session_state.ai_story = None
if "user_solutions" not in st.session_state:
    st.session_state.user_solutions = []
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "end_time" not in st.session_state:
    st.session_state.end_time = None
if "elapsed_time" not in st.session_state:
    st.session_state.elapsed_time = None
if "current_user" not in st.session_state:
    st.session_state.current_user = None


st.title("SQL Murder Mystery Game")

# get unique user token from headers and add to session state
get_current_user()

col1, col2 = st.columns(2)

with col1:
    if st.button("Generate Story"):
        
        # create temporary schema and tables for the current user
        with st.spinner("Loading temporary environment..."):
            try:
                create_schema_and_tables(schema_name=st.session_state.current_user)

            # handle situation when schema already exists for a user, reset tables
            except ProgrammingError:
                run_queries_in_schema(schema_name=st.session_state.current_user,
                          query_list=delete_queries)

        
        # run the workflow
        try:
            result = asyncio.run(run_workflow())
            
            # add to session state
            st.session_state.ai_story = result['story']
            st.session_state.start_time = time.time()

        except Exception as e:
            st.error("Oops...something went wrong. Please try again!")
            # for debugging
            st.error(e)


with col2:
    with st.expander('See Schema'):
        st.image('https://queryhunt-game-assets.s3.us-east-1.amazonaws.com/schema.svg')

    sql_editor()

    col3, col4 = st.columns(2)

    with col3:
        check_solution()

    with col4:
        show_hint(hint_prompt=HINT_PROMPT)


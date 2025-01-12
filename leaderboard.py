import streamlit as st
from utils.utils import get_connection
import pandas as pd

st.title("Leaderboard 🏆")

query = "SELECT username, date, time_sec FROM leaderboard ORDER BY time_sec ASC LIMIT 10;"

@st.cache_data
def get_leaderboard(query):
    """
        Executes a SQL query to fetch leaderboard data and returns it as a DataFrame.

        Executes the provided SQL query, retrieves the result set, and converts it into a pandas DataFrame.

        Args:
            query (str): The SQL query to execute for fetching leaderboard data.

        Returns:
            pd.DataFrame: A DataFrame containing the query results with column names.
    """
    with get_connection(database="original_game_schema") as conn:
        with conn.cursor() as cursor:
            cursor.execute(query)
            data = cursor.fetchall()

            column_names = [desc[0] for desc in cursor.description]
            df = pd.DataFrame(data, columns=column_names)

            return df


df = get_leaderboard(query)

# change column names for better readability, capitalize, remove underscores
df.columns = df.columns.str.replace('_', ' ').str.capitalize()

# change time_sec to Time (in seconds)
df.rename(columns={'Time sec': 'Time (in seconds)'}, inplace=True)

# add rank column
df.insert(0, 'Rank', range(1, 1 + len(df)))

# display the result as df
st.dataframe(df, hide_index=True, width=600)


import os
from sqlglot import parse_one, errors
import json
import asyncio
from pydantic import BaseModel, ValidationError, conlist
import re
import traceback
from llama_index.core.workflow import (
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    Context,
    step,
)
import os
import streamlit as st
from utils.utils import (clean_string, is_valid_sql, is_non_destructive,
                   initiate_llm, run_queries_in_schema)


STORY_PROMPT = """
Write an engaging and creative story for a SQL murder mystery game.
The story should be based on the provided database schema.
---------------------
{dbml_schema}
---------------------
The objective of the game is to explore data in different tables using SQL and identify the murderer following the story.
The story should include the following sections:
---------------------
Plot
Characters
Objective
Description of tables (do not reveal admin-only Murderer table)
---------------------
The story will be presented to a player, so do not reveal the murderer or any hints.
Do not include any sample SQL queries or tables, it will be done in the next step.
The story should not be very long.
"""

QUERY_PROMPT = """
Using the SQL murder mystery story, come up with game data that will be inserted into the tables.
Refer to the below database schema, and return valid SQL Insert queries.
---------------------
{dbml_schema}
---------------------
Do not use any special characters and line breaks in the output.
Do not use quotes inside strings like 'At a friend's house' or 'Sara's job'.
Generate enough data for each table to allow interesting gameplay.
Include id's for each row.
Fill out the admin-only Murderer table with correct suspect ID and name for this game.
Return queries as JSON object with the following schema: 
---------------------
{schema}
---------------------
Do not return anything else
Here's the story to reference: 
---------------------
{story}
---------------------
"""

QUERY_REFLECTION_PROMPT = """
You already created this output previously:
---------------------
{wrong_answer}
---------------------
This caused an error: {error}
Fix the error and return the corrected output using your knowledge about this dbml schema:
---------------------
{dbml_schema}
---------------------
Do not include line breaks or any other special characters.
Do not add text: '```json'
The response must contain only valid Python dictionary with the following schema:
---------------------
{{
  "queries": [
    {{"query": "INSERT INTO Table;"}},
    {{"query": "INSERT INTO Table;"}}
  ]
}}
---------------------
"""

delete_queries = [
    "DELETE FROM Evidence;",
    "DELETE FROM Murderer;",
    "DELETE FROM Alibis;",
    "DELETE FROM CrimeScene;",
    "DELETE FROM Suspects;",
    "DELETE FROM Victim;"
]


# Define the Pydantic models
class Query(BaseModel):
    query: str


class QueryCollection(BaseModel):
    queries: list[Query]


# Define the events for the workflow
class StoryEvent(Event):
    story: str


class CreateTablesEvent(Event):
    output: str | dict


class CorrectedOutputEvent(Event):
    output: str | dict


class ValidationErrorEvent(Event):
    error: str
    wrong_output: str | dict


class ValidatedSqlEvent(Event):
    queries: dict


# initialize llm model
llm = initiate_llm()


# Define the workflow
class MysteryFlow(Workflow):

    # get unique user token from streamlit headers
    #user_token = st.context.headers["X-Streamlit-User"]
    user_token = 'test_user'

    # Read dbml schema doc
    file_path = "data/schema_dbml.txt"
    with open(file_path, "r") as file:
        dbml_schema = file.read()

    # Set maximum number of workflow reruns
    max_retries: int = 3

    @step(pass_context=True)
    async def generate_story(self, ctx: Context, ev: StartEvent) -> StoryEvent:

        response = llm.stream_complete(STORY_PROMPT.format(dbml_schema=self.dbml_schema))

        # Stream story to the UI
        placeholder = st.empty()
        full_story = ""
        for chunk in response:
            full_story += chunk.delta
            placeholder.markdown(full_story)

        # Store the full story in the context data
        ctx.data['story'] = full_story

        return StoryEvent(story=str(full_story))


    @step()
    async def generate_tables(self, ev: StoryEvent) -> CreateTablesEvent:
 
        prompt = QUERY_PROMPT.format(dbml_schema=self.dbml_schema,
                                     schema=QueryCollection.schema_json(), story=ev.story)
        response = llm.complete(prompt)

        return CreateTablesEvent(output=str(response.text))


    @step(pass_context=True)
    async def validate_sql(self, ctx: Context, ev: CreateTablesEvent | CorrectedOutputEvent) -> ValidatedSqlEvent | ValidationErrorEvent:

        try:
            # check if output is a string
            if isinstance(ev.output, str):
                print('the output is a string')
                print('the output is', ev.output)

                query_str = clean_string(ev.output)
                query_dict = json.loads(query_str)
            else:
                print('the output is a dict')
                print('the output is', ev.output)

                query_dict = ev.output

            # check if sql query if valid and non-destructive
            for query in query_dict['queries']:
                if not is_valid_sql(query['query']):
                    raise Exception("Invalid SQL syntax")
                if not is_non_destructive(query['query']):
                    raise Exception("Destructive SQL query detected")
                continue

        except Exception:
            full_traceback = traceback.format_exc()
            print('the error is', full_traceback)
            print("Validation failed, retrying...")

            return ValidationErrorEvent(error=str(full_traceback), wrong_output=ev.output)

        return ValidatedSqlEvent(queries=query_dict)


    @step(pass_context=True)
    async def execute_queries(self, ctx: Context, ev: ValidatedSqlEvent) -> StopEvent | ValidationErrorEvent:
        query_dict = ev.queries
        query_list = [query['query'] for query in query_dict['queries']]

        print('trying to execute queries')
        try:
            run_queries_in_schema(schema_name=self.user_token, query_list=query_list)

        except Exception as e:
            full_traceback = traceback.format_exc()
            print('the error is', full_traceback)
            print("Failed to execute insert queries...")
            return ValidationErrorEvent(error=str(full_traceback), wrong_output=query_dict)

        print('Queries executed successfully')

        return StopEvent(result={'story': ctx.data.get('story'), 'queries': query_dict})


    @step(pass_context=True)
    async def self_correct(self, ctx: Context, ev: ValidationErrorEvent) -> CorrectedOutputEvent | StopEvent:

        current_retries = ctx.data.get("retries", 0)

        if current_retries >= self.max_retries:
            run_queries_in_schema(schema_name=self.user_token,
                                  query_list=delete_queries)  # Reset tables if max retries are reached
            return StopEvent(result="Max retries reached")

        else:
            ctx.data["retries"] = current_retries + 1

            reflection_prompt = QUERY_REFLECTION_PROMPT.format(wrong_answer=str(ev.wrong_output),
                                                               dbml_schema=self.dbml_schema, error=str(ev.error))
            response = llm.complete(reflection_prompt)

            # Convert or extract the response to a suitable type
            if isinstance(response, str):
                output = response
            elif hasattr(response, 'to_dict'):
                output = response.to_dict()  # Assuming response has a `to_dict()` method
            else:
                output = str(response)  # Fallback to string conversion

        return CorrectedOutputEvent(output=output)


async def run_workflow():
    w = MysteryFlow(timeout=60, verbose=True)
    result = await w.run()
    return result

# if __name__ == "__main__":
#     asyncio.run(run_workflow())


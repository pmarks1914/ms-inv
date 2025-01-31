import psycopg2
import pandas as pd
from openai import AzureOpenAI
from dotenv import dotenv_values


get_env = dotenv_values(".env")

# Database credentials (replace with your actual credentials)
DB_URL = get_env['DB_URL']

# OpenAI credentials (using dotenv for security)
OPENAI_MODEL = get_env["AZURE_OPENAI_MODEL"]
OPENAI_ENDPOINT = get_env["AZURE_OPENAI_ENDPOINT"]
OPENAI_API_KEY = get_env["AZURE_OPENAI_API_KEY"]
OPENAI_API_VERSION = get_env["AZURE_OPENAI_VERSION"]

try:
    # Connect to PostgreSQL using the DB_URL
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()

    # SQL query (adjusted to get the desired data)
    query = """
    SELECT COUNT(*) AS active_user_count
    FROM inv_user
    """

    cursor.execute(query)
    active_user_count_data = cursor.fetchone()  # Fetch a single row

    # Check if data is retrieved successfully (optional)
    if active_user_count_data:
        active_user_count = active_user_count_data[0]  # Extract the count
        print(f"Active User Count: {active_user_count}")
    else:
        print("No data found from the query.")

        
    # cursor.execute(query)
    # sales_data = pd.DataFrame(cursor.fetchall(), columns=["email", "first_name"])

    # Format sales data for OpenAI prompt
    sales_summary = ""
    # for index, row in active_user_count_data.iterrows():
    #     sales_summary += f"{row['email']}: ${row['first_name']:.2f}\n"

    # OpenAI prompt
    openai_prompt = f"""
    Here's a summary of sales by product email:

    {active_user_count_data}

    Generate a short, concise summary of the top performing categories.
    """

    # Initialize Azure OpenAI client
    openai_client = AzureOpenAI(
        azure_endpoint=OPENAI_ENDPOINT,
        api_key=OPENAI_API_KEY,
        api_version=OPENAI_API_VERSION
    )

    # Call OpenAI API
    openai_response = openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": openai_prompt}]
    )

    openai_summary = openai_response.choices[0].message.content

    print("\nSales Analysis:")
    print(active_user_count_data)
    print("\nOpenAI Summary:")
    print(openai_summary)

except (Exception, psycopg2.Error) as error:
    print(f"Error: {error}")

finally:
    if conn:
        cursor.close()
        conn.close()
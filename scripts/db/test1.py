import psycopg2
import json

# Load config from JSON file
with open("config.json") as f:
    conn_info = json.load(f)

conn = None
cursor = None

try:
    # Connect to the PostgreSQL database
    conn = psycopg2.connect(**conn_info)
    cursor = conn.cursor()

    # Run a simple query
    cursor.execute("SELECT * FROM users;")
    rows = cursor.fetchall()

    # Print the results
    print("List of users:")
    for row in rows:
        print(row)

except Exception as e:
    print("Error:", e)

finally:
    if cursor is not None:
        cursor.close()
    if conn is not None:
        conn.close()

import sqlite3

class DBClient:
    def __init__(self, db_name):
        self.db_name = db_name

    def connect(self):
        """Connect to the SQLite database."""
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()

    def close(self):
        """Close the SQLite database connection."""
        self.conn.close()

    def execute_query(self, query, params=None):
        """Execute a database query."""
        self.connect()
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
        self.conn.commit()
        self.close()

    def create_table(self, create_table_sql):
        """Create a table in the database."""
        try:
            self.execute_query(create_table_sql)
        except sqlite3.Error as e:
            print(f"Error creating table: {e}")

    def insert_data(self, insert_query, data):
        """Insert data into the table."""
        try:
            self.execute_query(insert_query, data)
        except sqlite3.Error as e:
            print(f"Error inserting data: {e}")

    def fetch_data(self, query, params=None):
        """Fetch data from the database."""
        self.connect()
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
        rows = self.cursor.fetchall()
        self.close()
        return rows

    def update_data(self, update_query, data):
        """Update data in the database."""
        try:
            self.execute_query(update_query, data)
        except sqlite3.Error as e:
            print(f"Error updating data: {e}")

    def delete_data(self, delete_query, params=None):
        """Delete data from the database."""
        try:
            self.execute_query(delete_query, params)
        except sqlite3.Error as e:
            print(f"Error deleting data: {e}")

    def get_username_by_phone_number(self, phone_number):
        """Get username by phone number."""
        query = "SELECT username FROM callee WHERE phone_number = ?"
        result = self.fetch_data(query, (phone_number,))
        if result:
            return result[0][0]  # Return the first username found
        else:
            return None

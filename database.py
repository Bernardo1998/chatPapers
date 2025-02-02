import json
import os

class PaperDatabase:
    def __init__(self, db_file="papers.json"):
        """Initialize the database with a file path."""
        self.db_file = db_file
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Create the database file if it doesn't exist."""
        if not os.path.exists(self.db_file):
            with open(self.db_file, 'w') as f:
                json.dump({}, f)

    def _load_db(self):
        """Load the current state of the database."""
        with open(self.db_file, 'r') as f:
            return json.load(f)

    def _save_db(self, data):
        """Save the database state to file."""
        with open(self.db_file, 'w') as f:
            json.dump(data, f, indent=4)

    def search_paper(self, title):
        """
        Search for a paper by exact title match.
        Returns the paper's dictionary if found, None otherwise.
        """
        db = self._load_db()
        return db.get(title)

    def insert_paper(self, title, paper_dict):
        """
        Insert or update a paper in the database.
        Args:
            title (str): The paper's title
            paper_dict (dict): Dictionary containing paper features
        """
        db = self._load_db()
        db[title] = paper_dict
        self._save_db(db)

    def delete_paper(self, title):
        """
        Delete a paper from the database.
        Returns True if paper was found and deleted, False otherwise.
        """
        db = self._load_db()
        if title in db:
            del db[title]
            self._save_db(db)
            return True
        return False

    def save(self):
        """Save current database state to file."""
        db = self._load_db()
        self._save_db(db)


if __name__ == "__main__":
    # Create a database instance
    db = PaperDatabase()

    # Insert a paper
    db.insert_paper(
        "Machine Learning Basics",
        {
            "authors": ["John Doe", "Jane Smith"],
            "year": 2023,
            "keywords": ["ML", "introduction"]
        }
    )

    # Insert another paper with different features
    db.insert_paper(
        "Deep Learning Advanced",
        {
            "authors": ["Alice Johnson"],
            "citations": 150,
            "doi": "10.1234/example"
        }
    )

    # Search for a paper
    paper = db.search_paper("Machine Learning Basics")
    if paper:
        print(paper)  # Prints the paper's dictionary

    # Update a paper
    db.insert_paper(
        "Machine Learning Basics",
        {
            "authors": ["John Doe", "Jane Smith"],
            "year": 2023,
            "keywords": ["ML", "introduction"],
            "citations": 25  # Added new feature
        }
    )
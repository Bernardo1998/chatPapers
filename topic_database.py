import json
import os

class TopicDatabase:
    def __init__(self, db_file="topics.json"):
        """Initialize the topic database with a file path."""
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

    def search_topic(self, topic_name):
        """
        Search for a topic by exact name match.
        Returns the topic's dictionary if found, None otherwise.
        """
        db = self._load_db()
        return db.get(topic_name)

    def insert_topic(self, topic_name, topic_dict):
        """
        Insert or update a topic in the database.
        Args:
            topic_name (str): The topic's name
            topic_dict (dict): Dictionary containing topic information
        """
        db = self._load_db()
        db[topic_name] = topic_dict
        self._save_db(db)

    def delete_topic(self, topic_name):
        """
        Delete a topic from the database.
        Returns True if topic was found and deleted, False otherwise.
        """
        db = self._load_db()
        if topic_name in db:
            del db[topic_name]
            self._save_db(db)
            return True
        return False

    def list_topics(self) -> dict[str, str]:
        """
        List all topics and their descriptions in the database.
        
        Returns:
            dict[str, str]: Dictionary with topic names as keys and descriptions as values
        """
        db = self._load_db()
        return {
            topic: data.get('description', 'No description available')
            for topic, data in db.items()
        }

    def save(self):
        """Save current database state to file."""
        db = self._load_db()
        self._save_db(db)

if __name__ == "__main__":
    # Create a database instance
    db = TopicDatabase()

    # Insert a topic
    db.insert_topic(
        "Natural Language Processing",
        {
            "description": "Research area focusing on interaction between computers and human language",
            "current_status": "Active and rapidly evolving",
            "important_papers": [
                "Attention Is All You Need",
                "BERT: Pre-training of Deep Bidirectional Transformers"
            ],
            "key_subtopics": [
                "Machine Translation",
                "Text Classification",
                "Question Answering"
            ]
        }
    )

    # Insert another topic with different structure
    db.insert_topic(
        "Reinforcement Learning",
        {
            "description": "Area of machine learning concerned with how agents take actions in an environment",
            "current_status": "Growing, with focus on sample efficiency",
            "challenges": [
                "Sample efficiency",
                "Exploration vs exploitation",
                "Credit assignment"
            ],
            "breakthrough_papers": {
                "2015": "DQN Nature Paper",
                "2017": "AlphaGo Zero"
            }
        }
    )

    # Search for a topic
    topic = db.search_topic("Natural Language Processing")
    if topic:
        print(topic)  # Prints the topic's dictionary

    # Update a topic
    db.insert_topic(
        "Natural Language Processing",
        {
            "description": "Research area focusing on interaction between computers and human language",
            "current_status": "Active and rapidly evolving",
            "important_papers": [
                "Attention Is All You Need",
                "BERT: Pre-training of Deep Bidirectional Transformers",
                "GPT-3: Language Models are Few-Shot Learners"  # Added new paper
            ],
            "key_subtopics": [
                "Machine Translation",
                "Text Classification",
                "Question Answering",
                "Large Language Models"  # Added new subtopic
            ]
        }
    )

    # Example usage of list_topics
    topics = db.list_topics()
    print("\nAvailable Topics:")
    for topic, description in topics.items():
        print(f"- {topic}: {description}") 
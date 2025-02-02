from typing import Type, TypeVar, Any
from ollama import chat
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class OllamaClient:
    def __init__(self, model: str = 'llama2'):
        self.model = model
    
    def get_structured_response(self, prompt: str, output_model: Type[T]) -> T:
        """
        Get a structured response from the Ollama model
        
        Args:
            prompt: The input prompt
            output_model: The Pydantic model class to structure the output
            
        Returns:
            Structured response as the specified Pydantic model
        """
        response = chat(
            messages=[
                {
                    'role': 'user',
                    'content': prompt,
                }
            ],
            model=self.model,
            format=output_model.model_json_schema(),
        )
        
        return output_model.model_validate_json(response.message.content)

# Example usage
if __name__ == "__main__":
    class Country(BaseModel):
        name: str
        capital: str
        languages: list[str]
    
    client = OllamaClient(model='llama3.1')
    country = client.get_structured_response(
        prompt='Tell me about Canada.',
        output_model=Country
    )
    print(country)
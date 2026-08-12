import ollama

# 1. Define the Agent Wrapper
def query_agent(model_name, role, prompt):
    print(f"\n[ SYSTEM ] Loading {model_name} for role: {role}...")
    client = ollama.Client(host='http://127.0.0.1:11434')
    response = client.chat(model=model_name, messages=[
        {
            'role': 'system',
            'content': f"You are an expert {role}. Output ONLY the requested content."
        },
        {
            'role': 'user',
            'content': prompt
        }
    ])
    
    # The model is automatically unloaded by Ollama after a timeout,
    # but we will rely on sequential calls to keep VRAM clear.
    return response['message']['content']

# 2. Test the 'Requirements Agent'
if __name__ == "__main__":
    user_input = "I want a simple calculator function in Python that adds two numbers."
    print(f"User Input: {user_input}")

    requirements = query_agent(
        model_name="llama3.1", # Changed from llama3.2:3b to match models installed in this project
        role="Product Manager",
        prompt=f"Convert this into a single User Story: {user_input}"
    )
    
    print(f"\n--- Requirements Agent Output ---\n{requirements}")

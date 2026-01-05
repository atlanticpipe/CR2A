from strands import Agent
from strands_tools import calculator, http_request

# Create an agent with community tools (uses Bedrock Claude 4 Sonnet by default)
# Note: Excluding python_repl due to Windows compatibility issues
agent = Agent(
    tools=[calculator, http_request],
    system_prompt="You are an expert in the international space station and geography."
)

# Test the agent
if __name__ == "__main__":
    print("🚀 Testing Strands Agent...")
    
    try:
        response = agent("Which city is the closest to the international space station right now?")
        print(f"Agent Response: {response}")
        
        # Test conversation memory
        print("\n🧠 Testing conversation memory...")
        agent("My name is Alice")
        memory_response = agent("What's my name?")
        print(f"Memory Response: {memory_response}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Make sure you have AWS credentials configured!")
        print("   Option 1: Set AWS_BEDROCK_API_KEY environment variable")
        print("   Option 2: Configure AWS credentials with 'aws configure'")
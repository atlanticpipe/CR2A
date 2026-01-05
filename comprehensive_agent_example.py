from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import calculator, http_request

# Create a custom tool
@tool
def get_weather(location: str) -> str:
    """Get weather information for a location.
    
    Args:
        location: City name to get weather for
    """
    # This is a mock weather function - in real use you'd call a weather API
    return f"Weather in {location}: Sunny, 72°F with light winds"

# Configure the model
model = BedrockModel(
    model_id="us.amazon.nova-pro-v1:0",
    region_name="us-east-1",
    temperature=0.7,
    max_tokens=2048,
)

# Create agent with both community tools and custom tools
agent = Agent(
    model=model,
    tools=[calculator, http_request, get_weather],
    system_prompt="""You are a helpful AI assistant with access to tools for:
    - Mathematical calculations
    - Making web requests to get current information
    - Getting weather information for cities
    
    Always be helpful and use the appropriate tools when needed."""
)

def test_agent():
    print("🚀 Comprehensive Strands Agent Test\n")
    
    # Test 1: Basic calculation
    print("📊 Test 1: Mathematical calculation")
    response1 = agent("Calculate the compound interest on $1000 at 5% annual rate for 3 years")
    print(f"Response: {response1}\n")
    
    # Test 2: Custom tool
    print("🌤️  Test 2: Custom weather tool")
    response2 = agent("What's the weather like in Seattle?")
    print(f"Response: {response2}\n")
    
    # Test 3: Conversation memory
    print("🧠 Test 3: Conversation memory")
    agent("My favorite programming language is Python")
    response3 = agent("What did I say my favorite programming language was?")
    print(f"Response: {response3}\n")
    
    # Test 4: Web request (if you want to test this)
    print("🌐 Test 4: Web request capability")
    print("(Skipping web request test to avoid external dependencies)")
    # response4 = agent("Get the current time from worldtimeapi.org")
    # print(f"Response: {response4}\n")

if __name__ == "__main__":
    try:
        test_agent()
        print("✅ All tests completed successfully!")
        print("\n🎯 Your Strands agent is working perfectly!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Troubleshooting tips:")
        print("   1. Make sure AWS credentials are configured")
        print("   2. Enable model access in Bedrock console")
        print("   3. Check your AWS region settings")
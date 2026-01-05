from strands import Agent
from strands.models import BedrockModel
from strands_tools import calculator, http_request

# Try with Amazon Nova model (might be available by default)
model = BedrockModel(
    model_id="us.amazon.nova-pro-v1:0",
    region_name="us-east-1",
    temperature=0.7,
    max_tokens=2048,
)

agent = Agent(
    model=model,
    tools=[calculator, http_request],
    system_prompt="You are a helpful assistant that can perform calculations and make web requests."
)

# Test the agent
if __name__ == "__main__":
    print("🚀 Testing Strands Agent with Amazon Nova...")
    
    try:
        response = agent("What is 15 * 23 + 100?")
        print(f"Agent Response: {response}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 You may need to enable model access in Bedrock console!")
        print("   1. Go to https://console.aws.amazon.com/bedrock")
        print("   2. Navigate to 'Model access' → 'Manage model access'")
        print("   3. Enable the models you want to use")
        print("   4. Wait a few minutes for access to be granted")
"""
Example showing how to use different model providers with Strands
"""
from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import calculator

@tool
def simple_greeting(name: str) -> str:
    """Generate a personalized greeting.
    
    Args:
        name: Person's name to greet
    """
    return f"Hello {name}! Nice to meet you!"

def create_bedrock_agent():
    """Create an agent using Amazon Bedrock (Nova)"""
    model = BedrockModel(
        model_id="us.amazon.nova-pro-v1:0",
        region_name="us-east-1",
        temperature=0.3,  # Lower temperature for more consistent responses
        max_tokens=1024,
    )
    
    return Agent(
        model=model,
        tools=[calculator, simple_greeting],
        system_prompt="You are a helpful assistant. Be concise and friendly."
    )

def test_different_providers():
    print("🤖 Multi-Provider Strands Agent Examples\n")
    
    # Test Bedrock (working)
    print("🟢 Amazon Bedrock (Nova Pro) - WORKING")
    bedrock_agent = create_bedrock_agent()
    response = bedrock_agent("Calculate 25 * 4 and then greet me as Alice")
    print(f"Response: {response}\n")
    
    # Show how to use other providers (commented out since they need API keys)
    print("📝 Other Provider Examples (require API keys):")
    print("""
    # Anthropic Direct
    from strands.models.anthropic import AnthropicModel
    model = AnthropicModel(
        client_args={"api_key": os.environ["ANTHROPIC_API_KEY"]},
        model_id="claude-sonnet-4-20250514",
        max_tokens=1028,
        params={"temperature": 0.7}
    )
    
    # OpenAI
    from strands.models.openai import OpenAIModel
    model = OpenAIModel(
        client_args={"api_key": os.environ["OPENAI_API_KEY"]},
        model_id="gpt-5-mini",
    )
    
    # Google Gemini
    from strands.models.gemini import GeminiModel
    model = GeminiModel(
        client_args={"api_key": os.environ["GOOGLE_API_KEY"]},
        model_id="gemini-2.5-pro",
    )
    """)

if __name__ == "__main__":
    try:
        test_different_providers()
        print("✅ Multi-provider example completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

# Installation commands for other providers:
print("""
🔧 To use other providers, install the extensions:

pip install 'strands-agents[anthropic]'  # For Anthropic Claude
pip install 'strands-agents[openai]'     # For OpenAI GPT  
pip install 'strands-agents[gemini]'     # For Google Gemini
pip install 'strands-agents[llamaapi]'   # For Meta Llama

Then set the appropriate API keys as environment variables.
""")
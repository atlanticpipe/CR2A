# Q&A Skills

## When to Use Query

Use `query_contract` for free-form questions that don't map to a specific category or checklist item:
- "What are the payment terms?"
- "Does the contract mention liquidated damages for late completion?"
- "Summarize section 5 of the contract"
- "Compare the indemnification and insurance requirements"

## Tips for Effective Queries

- Be specific in your questions for better results
- The query engine searches the full contract text, not just analysis results
- For very specific clause lookups, prefer `analyze_contract_category` instead
- For bid-specific values, prefer `analyze_bid_item` instead

## When to Answer Directly

If previous analysis results already contain the answer, respond directly without calling a tool. Check the conversation history for prior tool results before making a new call.

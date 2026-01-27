/**
 * JSON Extraction Utilities
 * 
 * Provides robust JSON extraction from LLM responses that may contain:
 * - Direct JSON
 * - JSON wrapped in markdown code blocks
 * - JSON surrounded by explanatory text
 * - Malformed responses requiring pattern-based extraction
 */

/**
 * Extract JSON from a response string using multi-stage extraction logic
 * 
 * @param {string} text - The response text that may contain JSON
 * @returns {Object} - The extracted and parsed JSON object
 * @throws {Error} - If JSON cannot be extracted or parsed
 */
export function extractJSON(text) {
  if (!text || typeof text !== 'string') {
    throw new Error('Invalid input: text must be a non-empty string');
  }

  // Stage 1: Try direct parsing
  try {
    return JSON.parse(text);
  } catch (e) {
    // Continue to next stage
  }

  // Stage 2: Try extracting from markdown code blocks
  const markdownMatch = text.match(/```(?:json)?\s*\n?([\s\S]*?)\n?```/);
  if (markdownMatch) {
    try {
      return JSON.parse(markdownMatch[1].trim());
    } catch (e) {
      // Continue to next stage
    }
  }

  // Stage 3: Try pattern-based extraction (find JSON object boundaries)
  const jsonObjectMatch = text.match(/\{[\s\S]*\}/);
  if (jsonObjectMatch) {
    try {
      return JSON.parse(jsonObjectMatch[0]);
    } catch (e) {
      // Continue to next stage
    }
  }

  // All extraction attempts failed
  throw new Error('Failed to extract valid JSON from response. Response may be malformed or not contain JSON.');
}

/**
 * Validate that a JSON object contains all required CR2A fields
 * 
 * @param {Object} jsonObject - The parsed JSON object to validate
 * @returns {boolean} - True if all required fields are present
 * @throws {Error} - If required fields are missing
 */
export function validateCR2AFields(jsonObject) {
  if (!jsonObject || typeof jsonObject !== 'object') {
    throw new Error('Invalid input: jsonObject must be an object');
  }

  const requiredFields = [
    'Clause Summary',
    'Risk Triggers Identified',
    'Flow-Down Obligations',
    'Redline Recommendations',
    'Harmful Language / Policy Conflicts',
    'risk_level'
  ];

  const missingFields = requiredFields.filter(field => !(field in jsonObject));

  if (missingFields.length > 0) {
    throw new Error(`Missing required CR2A fields: ${missingFields.join(', ')}`);
  }

  // Validate risk_level has a valid value
  const validRiskLevels = ['high', 'moderate', 'low'];
  if (!validRiskLevels.includes(jsonObject.risk_level)) {
    throw new Error(`Invalid risk_level: "${jsonObject.risk_level}". Must be one of: ${validRiskLevels.join(', ')}`);
  }

  return true;
}

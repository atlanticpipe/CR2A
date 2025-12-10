import { defineBackend, restApi, defineFunction } from "@aws-amplify/backend";
import { Runtime } from "aws-cdk-lib/aws-lambda";

// Lambda function wrapping the CR2A API stub; Amplify injects environment values at deploy time.
const cr2aApiHandler = defineFunction({
  name: "cr2aApiHandler",
  entry: "./functions/cr2a-api",
  handler: "app.lambda_handler",
  runtime: Runtime.PYTHON_3_12,
  timeoutSeconds: 30,
  environment: {
    AWS_REGION: process.env.AWS_REGION ?? process.env.AWS_DEFAULT_REGION ?? "",
    UPLOAD_BUCKET: process.env.UPLOAD_BUCKET ?? "",
    OUTPUT_BUCKET: process.env.OUTPUT_BUCKET ?? "",
    MAX_FILE_MB: process.env.MAX_FILE_MB ?? "500",
    UPLOAD_EXPIRES_SECONDS: process.env.UPLOAD_EXPIRES_SECONDS ?? "3600",
    MAX_ANALYSIS_SECONDS: process.env.MAX_ANALYSIS_SECONDS ?? "900",
  },
});

// REST API surface that maps all routes to the Lambda stub for now.
const backend = defineBackend({
  api: restApi({
    name: "cr2a-api",
    routes: {
      "ANY /": cr2aApiHandler,
      "ANY /{proxy+}": cr2aApiHandler,
    },
  }),
});

// Expose the API URL so the webapp build can pick it up from amplify_outputs.json.
backend.addOutput({
  custom: {
    apiGatewayUrl: backend.api.url,
  },
});

#!/usr/bin/env python3
"""
Find your existing AWS resources for the CR2A project.
"""

import boto3
import json
from botocore.exceptions import ClientError, NoCredentialsError

def find_lambda_functions():
    """Find Lambda functions that might be related to CR2A."""
    print("Looking for Lambda functions...")
    try:
        lambda_client = boto3.client('lambda', region_name='us-east-1')
        response = lambda_client.list_functions()
        
        cr2a_functions = []
        for func in response['Functions']:
            name = func['FunctionName']
            if any(keyword in name.lower() for keyword in ['cr2a', 'contract', 'analysis']):
                cr2a_functions.append(func)
        
        if cr2a_functions:
            print("Found potential CR2A Lambda functions:")
            for func in cr2a_functions:
                print(f"{func['FunctionName']}")
                print(f"Runtime: {func['Runtime']}")
                print(f"Handler: {func['Handler']}")
                print(f"Last Modified: {func['LastModified']}")
                print()
        else:
            print("No CR2A-related Lambda functions found")
            print("All functions:")
            for func in response['Functions']:
                print(f"{func['FunctionName']}")
        
        return cr2a_functions
        
    except NoCredentialsError:
        print("AWS credentials not configured. Run 'aws configure' first.")
        return []
    except Exception as e:
        print(f"Error listing Lambda functions: {e}")
        return []

def find_s3_buckets():
    """Find S3 buckets that might be related to CR2A."""
    print("Looking for S3 buckets...")
    try:
        s3_client = boto3.client('s3', region_name='us-east-1')
        response = s3_client.list_buckets()
        
        cr2a_buckets = []
        for bucket in response['Buckets']:
            name = bucket['Name']
            if any(keyword in name.lower() for keyword in ['cr2a', 'contract', 'upload', 'output']):
                cr2a_buckets.append(bucket)
        
        if cr2a_buckets:
            print("Found potential CR2A S3 buckets:")
            for bucket in cr2a_buckets:
                print(f"{bucket['Name']}")
                print(f"Created: {bucket['CreationDate']}")
                
                # Try to get bucket region
                try:
                    region_response = s3_client.get_bucket_location(Bucket=bucket['Name'])
                    region = region_response.get('LocationConstraint') or 'us-east-1'
                    print(f"Region: {region}")
                except:
                    print(f"Region: unknown")
                print()
        else:
            print("No CR2A-related S3 buckets found")
            print("All buckets:")
            for bucket in response['Buckets']:
                print(f"   {bucket['Name']}")
        
        return cr2a_buckets
        
    except Exception as e:
        print(f"Error listing S3 buckets: {e}")
        return []

def find_api_gateways():
    """Find API Gateways that might be related to CR2A."""
    print("Looking for API Gateways...")
    try:
        apigateway_client = boto3.client('apigateway', region_name='us-east-1')
        response = apigateway_client.get_rest_apis()
        
        cr2a_apis = []
        for api in response['items']:
            name = api['name']
            if any(keyword in name.lower() for keyword in ['cr2a', 'contract', 'analysis']):
                cr2a_apis.append(api)
        
        if cr2a_apis:
            print("Found potential CR2A API Gateways:")
            for api in cr2a_apis:
                print(f"      {api['name']} (ID: {api['id']})")
                print(f"      Created: {api['createdDate']}")
                
                # Get stages
                try:
                    stages_response = apigateway_client.get_stages(restApiId=api['id'])
                    for stage in stages_response['item']:
                        stage_name = stage['stageName']
                        url = f"https://{api['id']}.execute-api.us-east-1.amazonaws.com/{stage_name}"
                        print(f"      Stage: {stage_name} -> {url}")
                except:
                    pass
                print()
        else:
            print("No CR2A-related API Gateways found")
            print("   All APIs:")
            for api in response['items']:
                print(f"   {api['name']} (ID: {api['id']})")
        
        return cr2a_apis
        
    except Exception as e:
        print(f"Error listing API Gateways: {e}")
        return []

def main():
    """Find all CR2A-related AWS resources."""
    print("Searching for your existing CR2A AWS resources...")
    print("=" * 60)
    
    lambda_functions = find_lambda_functions()
    print()
    
    s3_buckets = find_s3_buckets()
    print()
    
    api_gateways = find_api_gateways()
    print()
    
    print("=" * 60)
    print("Summary:")
    print(f"Lambda Functions: {len(lambda_functions)}")
    print(f"S3 Buckets: {len(s3_buckets)}")
    print(f"API Gateways: {len(api_gateways)}")
    
    if lambda_functions or s3_buckets or api_gateways:
        print("\n Next steps:")
        if lambda_functions:
            print(f"1. Update Lambda function: python update_existing_lambda.py")
            print(f"Use function name: {lambda_functions[0]['FunctionName']}")
        if api_gateways:
            print(f"2. Test your API endpoints using the URLs shown above")
        if s3_buckets:
            print(f"3. Verify S3 bucket permissions and CORS settings")
    else:
        print("\n No existing CR2A resources found.")
        print("You may need to create them first or check your AWS region/credentials.")

if __name__ == "__main__":
    main()
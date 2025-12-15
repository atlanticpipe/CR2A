"""Lambda handler wrapper for CR2A API"""
import json
import logging
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """Main Lambda handler with comprehensive error logging"""
    logger.info("="*80)
    logger.info("Lambda handler invoked")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Directory contents: {os.listdir('.')}")
    logger.info(f"Event type: {type(event)}")
    logger.info(f"Event keys: {event.keys() if isinstance(event, dict) else 'Not a dict'}")
    logger.info("="*80)
    
    try:
        # Log the import attempt
        logger.info("Attempting to import Mangum handler from src.api.main")
        from src.api.main import handler as mangum_handler
        logger.info("Successfully imported Mangum handler")
        logger.info(f"Handler type: {type(mangum_handler)}")
        
        # Call the actual handler
        logger.info("Calling Mangum handler...")
        result = mangum_handler(event, context)
        logger.info(f"Handler completed successfully")
        logger.info(f"Result type: {type(result)}")
        logger.info(f"Result: {json.dumps(result) if isinstance(result, dict) else str(result)}")
        
        return result
        
    except ImportError as e:
        logger.error(f"ImportError: {str(e)}")
        logger.error(f"sys.path: {sys.path}")
        logger.error(f"Available modules in current directory:")
        try:
            for item in os.listdir('.'):
                logger.error(f"  - {item}")
        except Exception as list_err:
            logger.error(f"Could not list directory: {list_err}")
        
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Import Error',
                'message': str(e),
                'type': 'ImportError'
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Lambda Execution Error',
                'message': str(e),
                'type': type(e).__name__
            })
        }

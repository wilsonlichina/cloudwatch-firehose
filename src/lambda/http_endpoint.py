import json
import time

def lambda_handler(event, context):
    print("Received event:", event)

    body = {
        "requestId": event["headers"]["X-Amz-Firehose-Request-Id"],
        "timestamp": int(time.time() * 1000)
    }

    # Parse the body string into a dictionary
    try:
        request_body = json.loads(event["body"]) if event.get("body") else {}
        records = request_body.get("records", [])
        processed_records = []
            
        for record in records:
            # Add your record processing logic here
            processed_records.append(record)

        # print("Processed records:", processed_records)

        output = {
            "statusCode": 200,
            "body": json.dumps(body),
            "headers": {
                "Content-Type": "application/json"
            }
        }
        print("Output:", output)
        return output

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(e)}),
            "headers": {
                "Content-Type": "application/json"
            }
        }

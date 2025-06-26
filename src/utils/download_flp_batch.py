import json
from email.utils import format_datetime

from src.utils import httpHelper
from src.utils.parse_access_token import get_access_token
from src.utils.downloadFP import download_all_final_floorplans


def init_auth_token():
    auth_token = get_access_token()
    return auth_token

if __name__ == '__main__':
    auth_token = init_auth_token()
    fromDate = "2025-01-15T00:00:00.000Z"
    page = 0  # Start from page 0
    total_properties = 0
    
    while True:
        print(f"Fetching page {page}...")
        propertiesList = httpHelper.getPropertySummaries(fromDate, page, auth_token).json()['content']
        
        if not propertiesList:  # If no more properties, break the loop
            print("No more properties found.")
            break
            
        print(f"Found {len(propertiesList)} properties on page {page}")
        total_properties += len(propertiesList)
        
        for i in range(0, len(propertiesList)):
            orderId = propertiesList[i]['orderId']
            property_details = httpHelper.getPropertyByOrderId(orderId, auth_token).json()['content'][0]
            processedCaptureId = (property_details['processedCaptureId'])
            print(f"Processing capture ID: {processedCaptureId}")
            print(f"Property Published Status: {property_details['published']}")
            
            # Save the processed capture ids to a file
            with open('processed_capture_ids.txt', 'a') as f:
                f.write(str(processedCaptureId) + '\n')
        
        page += 1  # Move to next page
    
    print(f"\nProcessing complete! Total properties processed: {total_properties}")



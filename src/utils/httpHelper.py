import requests
import json

def getStagingCapture(capture_id, staging_auth_token):
    url = f"https://apiproxy.test.hellopupil.com/capture/v1/captures/{capture_id}?accept=application/vnd.pupil.published-capture+json&"

    payload = {}
    headers = {
        'Authorization': staging_auth_token
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    return response



def getPropertyByOrderId(orderId, auth_token):
    URL = f"https://pupil-api.hellopupil.com/property/v1/properties?lightweight=true&orderId={orderId}"
    headers = {
        "Authorization": auth_token
    }

    payload = {}
    response = requests.request("GET", URL, headers=headers, data=payload)

    return response


def getPropertySummaries(fromDate,page, auth_token):
    URL = f"https://pupil-api.hellopupil.com/property/v1/property-summaries?fromDate={fromDate}&published=true&page={page}"
    headers = {
        'Authorization': auth_token
    }
    payload = {}
    response = requests.request("GET", URL, headers=headers, data=payload)

    return response

def getProcessedCaptureFloorplan(florplanId, missionControlAuthToken):
    URL = "http://apiproxy.prod.hellopupil.com/processed-capture/v1/floorplans/{}".format(florplanId)

    headers = {
        'Accept': "application/vnd.pupil.full-floorplan+json",
        'Authorization': missionControlAuthToken
    }

    response = requests.request("GET", URL, headers=headers)

    return response

def getProcessedScenes(processedCaptureId, missionControlAuthToken):
    url = "http://apiproxy.prod.hellopupil.com/processed-capture/v1/processedScenes"

    querystring = {"page": "0", "processedCaptureId":processedCaptureId, "size": "1000", "sort": "created,DESC"}

    payload = ""
    headers = {
        'Accept' : "application/vnd.pupil.full-processed-scene+json",
        'Authorization': missionControlAuthToken
    }

    response = requests.request("GET", url, data=payload, headers=headers, params=querystring)

    return response
    headers = {
        'Accept': "application/vnd.pupil.full-processed-capture+json",
        'Authorization': missionControlAuthToken,
        'User-Agent': "PostmanRuntime/7.15.2",
        'Cache-Control': "no-cache",
        'Postman-Token': "a0c496c3-32f0-4518-8d0a-abda215438d0,4f974ae0-f43c-4a5c-ba90-6694d804f64a",
        'Host': "apiproxy.prod.hellopupil.com",
        'Accept-Encoding': "gzip, deflate",
        'Connection': "keep-alive",
        'cache-control': "no-cache"
    }

    response = requests.request("GET", URL, headers=headers)

    return response

# def create_processed_capture_scene_staging(processed_capture_id: int):
#     auth_token = get_access_token_staging()
#     URL = "https://apiproxy.test.hellopupil.com/processed-capture/v1/processedCaptures/14233/processedScenes"
#     headers = {
#         'Authorization': auth_token,
#         'accept': "application/json",
#         'Content-Type': "application/json"
#     }
#     # raw_scene_id = str(uuid.uuid4())
#     raw_scene_id = "58a11b82-285e-4f46-9712-e374cb8ace51"
#     print(raw_scene_id)
#
#     payload = {
#         "name": "testScene1",
#         "floor": 0,
#         "type": "BEDROOM",
#         "displayOrder": 0,
#         "publishedState": "PUBLISHED",
#         "vtPublishedState": "PUBLISHED",
#         "rawSceneId": raw_scene_id
#
#     }
#     json_payload = json.dumps(payload)
#
#     response = requests.request("POST", URL, headers=headers, data=json_payload)
#     print(response.text)
#     return response


def getFloorplanResponse(intId, sectionId, floorplanID, missionControlAuthToken):
    URL = "https://dimensions.hellopupil.com/api/processedCaptures/{}/sections/{}/floorplans/{}".format(intId, sectionId, floorplanID)
    # URL = "https://dimensions.hellopupil.com/api/processedCaptures/{}/sections/{}/versions/draft-{}".format(intId, sectionId,draftId)

    payload = ""
    headers = {
        'Authorization': missionControlAuthToken,
        'cache-control': "no-cache",
        'Postman-Token': "0b10414e-d313-4de0-9e56-0ea8d642b701"
    }

    response = requests.request("GET", URL, data=payload, headers=headers)
    return response


def getProcessedCapture(intId, missionControlAuthToken):
    URL = "http://apiproxy.prod.hellopupil.com/processed-capture/v1/processedCaptures/{}".format(intId)

    headers = {
        'Accept': "application/vnd.pupil.full-processed-capture+json",
        'Authorization': missionControlAuthToken,
        'User-Agent': "PostmanRuntime/7.15.2",
        'Cache-Control': "no-cache",
        'Postman-Token': "a0c496c3-32f0-4518-8d0a-abda215438d0,4f974ae0-f43c-4a5c-ba90-6694d804f64a",
        'Host': "apiproxy.prod.hellopupil.com",
        'Accept-Encoding': "gzip, deflate",
        'Connection': "keep-alive",
        'cache-control': "no-cache"
    }

    response = requests.request("GET", URL, headers=headers)

    return response


def getProcessedCaptures(missionControlAuthToken):
    url = "http://apiproxy.prod.hellopupil.com/processed-capture/v1/processedCaptures"

    querystring = {"page": "0", "size": "50", "sort": "created,DESC"}

    payload = ""
    headers = {
        'Authorization': missionControlAuthToken,
        'cache-control': "no-cache",
        'Postman-Token': "40388bee-6d59-4aca-970b-b143f7399abd"
    }

    response = requests.request("GET", url, data=payload, headers=headers, params=querystring)

    return response

def getCaptureStatus(rawCapId, missionControlAuthToken):
    url = "https://pupil-api.hellopupil.com/order/v1/orders/"

    querystring = {"captureId": rawCapId}

    payload = ""
    headers = {
        'Authorization': missionControlAuthToken,
        'cache-control': "no-cache",
        'Postman-Token': "2cc76616-f3bc-4a2b-8d23-3911704c9aba"
    }

    response = requests.request("GET", url, data=payload, headers=headers, params=querystring)
    return response

def getSections(intId, missionControlAuthToken):
    url = "https://dimensions.hellopupil.com/api/processedCaptures/{}/sections".format(intId)

    payload = ""
    headers = {
        'Authorization': missionControlAuthToken,
        'cache-control': "no-cache",
        'Postman-Token': "0c12c343-e216-4eae-b24d-48ae4de70990"
    }

    response = requests.request("GET", url, data=payload, headers=headers)
    return response


def getBeautifiedFloorplan(processedCapId, path_to_output, missionControlAuthToken):
    url = "http://apiproxy.prod.hellopupil.com/processed-capture/v1/floorplans"

    querystring = {"processedCaptureId": processedCapId}

    payload = ""
    headers = {
        'Authorization': missionControlAuthToken,
        'User-Agent': "PostmanRuntime/7.11.0",
        'Accept': "*/*",
        'Cache-Control': "no-cache",
        'Postman-Token': "2c27b0d6-7a38-4340-aa67-d75891282b75,7b6f14d5-37d8-42b3-b5b9-89e830afee8f",
        'Host': "apiproxy.prod.hellopupil.com",
        'accept-encoding': "gzip, deflate",
        'Connection': "keep-alive",
        'cache-control': "no-cache"
    }

    response = requests.request("GET", url, data=payload, headers=headers, params=querystring)
    fpResp_json = response.json()

    fp_content = fpResp_json['content']
    for i in range(0, len(fp_content)):
        pubState = fp_content[i]['publishedState']
        if (pubState == 'PUBLISHED'):
            bucket = fp_content[i]['mediaReference']['bucket']
            path = fp_content[i]['mediaReference']['path']
            if (path[-3:] == "png"):
                print(bucket, path)
                print("https://{}.s3-eu-west-1.amazonaws.com/{}".format(bucket, path))
                url = "https://{}.s3-eu-west-1.amazonaws.com/{}".format(bucket, path)
                r = requests.get(url, allow_redirects=True)
                filename = "{}{}.png".format(path_to_output,processedCapId)
                open(filename, 'wb').write(r.content)
                return True
    # print(response.text)

    return False


# if __name__ == '__main__':
#     create_processed_capture_scene_staging(14233)

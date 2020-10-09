#!/usr/bin/env bash

API_KEY=--------------MISSING--------------------------
SERVER=https://pero-ocr.fit.vutbr.cz/api

REQUEST_JSON='{"engine": 1,"images": {
"00061140-d108-11e6-bf97-005056825209": "https://kramerius.mzk.cz/search/iiif/uuid:00061140-d108-11e6-bf97-005056825209/full/full/0/default.jpg",
"00a0c240-26e2-11e8-b8a6-5ef3fc9ae867": "https://kramerius.mzk.cz/search/iiif/uuid:00a0c240-26e2-11e8-b8a6-5ef3fc9ae867/full/full/0/default.jpg",
} } '
curl ${SERVER}/get_engines --header "api-key: $API_KEY"
curl ${SERVER}/post_processing_request --request POST --data "$REQUEST_JSON" --header "api-key: $API_KEY" --header "Content-Type: application/json"

REQUEST_ID=--------------MISSING--------------------------
curl ${SERVER}/request_status/${REQUEST_ID} --header "api-key: $API_KEY"
for i in txt alto xml
do
    curl "${SERVER}/download_results/${REQUEST_ID}/00061140-d108-11e6-bf97-005056825209/${i}" --header "api-key: $API_KEY" | wc
done


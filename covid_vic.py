from parsec import *
from datetime import datetime
from clize import run
from copy import deepcopy
import requests
import json
from bson.json_util import dumps, CANONICAL_JSON_OPTIONS

datasource = 'https://discover.data.vic.gov.au/api/3/action/datastore_search?resource_id=afb52611-6061-4a2b-9110-74c920bede77&limit=10000'

p_time = regex(r'[0-9]+(:[0-9]+)?(am|pm)')
p_from_to_time = sepBy(p_time, string(' - '))

places = ['Coles', 'Woolworth', 'Chemist']

def chain(start, funcs):
    res = start
    for func in funcs:
        res = func(res)
    return res

def get_data(url):
    res = requests.get(url).text.encode('ascii', 'ignore').decode()
    res = json.loads(res)['result']['records']
    return res

def timeparse(ff):
    res = ff
    if ':' not in ff:
        res = f'{ff[:-2]}:00{ff[-2:]}'
    return datetime.strptime(res, '%I:%M%p').strftime('%H:%M')

def map_datetime(doc):
    time_parsed = p_from_to_time.parse(doc['Exposure_time'])
    if len(time_parsed) < 2:
        return doc
    time_start = timeparse(time_parsed[0])
    time_end = timeparse(time_parsed[1])
    datetime_start = datetime.strptime(f"{doc['Exposure_date']} {time_start}", '%d/%m/%Y %H:%M')
    datetime_end = datetime.strptime(f"{doc['Exposure_date']} {time_end}", '%d/%m/%Y %H:%M')
    doc['start_datetime'] = datetime_start
    doc['end_datetime'] = datetime_end
    doc['start_time'] = time_start
    doc['end_time'] = time_end
    return doc

def map_place(doc):
    res = [x for x in places if doc['Site_title'].startswith(x)]
    doc['place'] = res[0] if res else 'others'
    return doc

def main():
    docs = get_data(datasource)
    for doc in docs:
        d = chain(doc, [map_datetime, map_place])
        print(dumps(d, json_options=CANONICAL_JSON_OPTIONS))

if __name__ == '__main__':
    run(main)



example_entry = {
    "Added_date": "07/08/2021",
    "Added_date_dtm": "2021-08-07",
    "Added_time": "15:00:00",
    "Advice_instruction": "Anyone who has visited this location during these times should urgently get tested, then isolate until confirmation of a negative result. Continue to monitor for symptoms, get tested again if symptoms appear.",
    "Advice_title": "Tier 2 - Get tested urgently and isolate until you have a negative result",
    "Exposure_date": "04/08/2021",
    "Exposure_date_dtm": "2021-08-04",
    "Exposure_time": "5:45pm - 6:35pm",
    "Exposure_time_end_24": "18:35:00",
    "Exposure_time_start_24": "17:45:00",
    "Notes": "Case attended venue",
    "Site_postcode": "3030",
    "Site_state": "VIC",
    "Site_streetaddress": "Corner Cherry Street & Watton Street ",
    "Site_title": "Woolworths Werribee",
    "Suburb": "Werribee",
    "_id": 51
}

def test_map_datetime():
    res = map_datetime(example_entry)
    assert res['start_datetime'] == datetime(2021, 8, 4, 17, 45)
    assert res['end_datetime'] == datetime(2021, 8, 4, 18, 35)

def test_map_place():
    res = map_place(example_entry)
    assert res['place'] == 'Woolworth'

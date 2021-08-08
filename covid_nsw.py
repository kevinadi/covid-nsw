from parsec import *
from datetime import datetime
from clize import run
from copy import deepcopy
import requests
import json
from bson.json_util import dumps, CANONICAL_JSON_OPTIONS

datasource = 'https://data.nsw.gov.au/data/dataset/0a52e6c1-bc0b-48af-8b45-d791a6d8e289/resource/f3a28eed-8c2a-437b-8ac1-2dab3cf760f9/download'

p_time = regex(r'[0-9]+(:[0-9]+)?(am|pm)')
p_from_to_time = sepBy(p_time, string(' to '))

places = ['Coles', 'Woolworth', 'Chemist']

def chain(start, funcs):
    res = start
    for func in funcs:
        res = func(res)
    return res

def get_data(url):
    res = requests.get(url).text.encode('ascii', 'ignore').decode()
    res = json.loads(res)['data']['monitor']
    return res

def timeparse(ff):
    res = ff
    if ':' not in ff:
        res = f'{ff[:-2]}:00{ff[-2:]}'
    return datetime.strptime(res, '%I:%M%p').strftime('%H:%M')

def map_datetime(doc):
    time_parsed = p_from_to_time.parse(doc['Time'])
    if len(time_parsed) < 2:
        return doc
    time_start = timeparse(time_parsed[0])
    time_end = timeparse(time_parsed[1])
    datetime_start = datetime.strptime(f"{doc['Date']} {time_start}", '%A %d %B %Y %H:%M')
    datetime_end = datetime.strptime(f"{doc['Date']} {time_end}", '%A %d %B %Y %H:%M')
    doc['start_datetime'] = datetime_start
    doc['end_datetime'] = datetime_end
    doc['start_time'] = time_start
    doc['end_time'] = time_end
    return doc

def map_place(doc):
    res = [x for x in places if doc['Venue'].startswith(x)]
    doc['place'] = res[0] if res else 'others'
    return doc

def map_location(doc):
    try:
        loc = {
            'type': 'Point',
            'coordinates': [
                float(doc['Lon']),
                float(doc['Lat'])
            ]
        }
        doc['location'] = loc
    except ValueError as e:
        pass
    return doc

def map_id(doc):
    doc['_id'] = hash(f"{doc['Venue']} {doc['Date']} {doc['Time']} {doc['Last updated date']}")
    return doc

def map_place_suburb(doc):
    if not doc.get('place'):
        doc['place'] = map_place(doc)
    doc['place_suburb'] = ', '.join([doc['place'], doc['Suburb']])
    return doc

def main():
    docs = get_data(datasource)
    for doc in docs:
        d = chain(doc, [map_datetime, map_place, map_location, map_place_suburb])
        print(dumps(d, json_options=CANONICAL_JSON_OPTIONS))

if __name__ == '__main__':
    run(main)



example_entry = {'Venue': 'Woolworths Wolli Creek',
  'Address': '78-96 Arncliffe Street',
  'Suburb': 'Wolli Creek',
  'Date': 'Thursday 8 July 2021',
  'Time': '1pm to 1:40pm',
  'Alert': 'Monitor for symptoms.',
  'Lon': '151.153990382784',
  'Lat': '-33.930438041248',
  'HealthAdviceHTML': "Anyone who attended this venue must monitor for symptoms and if they occur <a href='https://www.nsw.gov.au/covid-19/how-to-protect-yourself-and-others/clinics'>get tested</a> immediately and <a href='https://www.nsw.gov.au/covid-19/what-you-can-and-cant-do-under-rules/self-isolation'>self-isolate</a> until you receive a negative result.",
  'Last updated date': 'Friday 16 July 2021'}

def test_timeparse():
    assert timeparse('1pm') == '13:00'
    assert timeparse('11am') == '11:00'

def test_map_datetime():
    res = map_datetime(example_entry)
    assert res['start_datetime'] == datetime(2021, 7, 8, 13, 0)
    assert res['end_datetime'] == datetime(2021, 7, 8, 13, 40)
    assert res['start_time'] == '13:00'
    assert res['end_time'] == '13:40'

def test_map_place():
    res = map_place(example_entry)
    assert res['place'] == 'Woolworth'

def test_map_place_suburb():
    res = map_place_suburb(example_entry)
    assert res['place_suburb'] == 'Woolworth, Wolli Creek'

def test_map_location():
    e = deepcopy(example_entry)
    e['Lon'], e['Lat'] = '', ''
    assert e.get('location') is None

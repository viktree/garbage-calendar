from __future__ import print_function
from datetime import datetime
import os
import re
import pickle
import os.path
import pandas as pd
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


UTC_TIME_INDICATOR = 'Z'
GARBAGE_DAY_INDICATOR = 'T'
SERVICE_NAME = 'calendar'
API_VERSION = 'v3'
SCOPES = ['https://www.googleapis.com/auth/calendar']


CALENDER_ID = os.environ['CALENDER_ID']
DISTRICT_ID = os.environ['DISTRICT_ID']
CREDENTIALS_FILE = os.environ['CREDENTIALS_FILENAME'] + '.json'
TOKEN_FILE = os.environ['TOKEN_FILENAME'] + '.pickle'


def load_credentails():
    credentials = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            credentials = pickle.load(token)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            credentials = flow.run_local_server()

        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(credentials, token)

    return credentials


def make_event(events_api, calendarId, day_type, date):
    morning_time = date
    event = {
        'summary': day_type + ' Disposal',
        'start': {
            'date': date
        },
        'end': {
            'date': date
        },
    }
    events_api().insert(calendarId=calendarId, body=event).execute()


def get_events(events_api, calendarId, number_of_events):``
    now = datetime.utcnow().isoformat() + UTC_TIME_INDICATOR
    events_result = events_api().list(calendarId=calendarId,
                                    timeMin=now,
                                    maxResults=number_of_events,
                                    singleEvents=True,
                                    orderBy='startTime').execute()
    events = events_result.get('items', [])

    return events


def try_parsing_date(text):
    for fmt in ('%m/%d/%y', '%m/%d/%Y'):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass


def load_garbage_schedule_data():
    garbage_day_types = ['Garbage', 'Green Bin', 'Recycling', 'Yard Waste', ' Christmas Tree']
    full_schedule_data = pd.read_csv("./data/Pickup_Schedule_2019.csv")

    # Clean up the data
    col_with_booleans = lambda col: full_schedule_data[col] == GARBAGE_DAY_INDICATOR
    for col in garbage_day_types:
        full_schedule_data[col] = col_with_booleans(col)

    convert_date_fmt = lambda old_date_fmt: try_parsing_date(old_date_fmt).strftime("%Y-%m-%d")
    full_schedule_data['Week Starting'] = full_schedule_data['Week Starting'].apply(convert_date_fmt)

    # Extract the part that we want
    is_correct_ward = full_schedule_data['Calendar'] == DISTRICT_ID
    ward_schedule = full_schedule_data[is_correct_ward].drop(columns=['Calendar'])
    get_dates_of_type = lambda day_type: list(ward_schedule[ward_schedule[day_type]]['Week Starting'])
    return {day_type:get_dates_of_type(day_type) for day_type in garbage_day_types}


def main():
    garbage_days = load_garbage_schedule_data()
    credentials = load_credentails()
    gcal_service = build(SERVICE_NAME, API_VERSION, credentials=credentials)
    events_api = lambda :gcal_service.events()

    number_of_events = 10
    print('Getting the upcoming %d events' % number_of_events)
    events = get_events(events_api, CALENDER_ID, number_of_events)

    # for date_type in garbage_days.keys():
    #     for date in garbage_days[date_type]:
    #         make_event(events_api, CALENDER_ID, date_type, date)

    if not events:
        print('No upcoming events found.')

    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start, event['summary'])


if __name__ == '__main__':
    main()
# This file is not a part of the main project logic
# it is used to upload the CSVs provided into MySQL Database

from app import app
from app import db
from app.models import *
from app.helper import *
import pytz
from datetime import datetime
import pandas as pd

# Read the CSV files
store_status_df = pd.read_csv("static/storestatus.csv")
business_hours_df = pd.read_csv("static/businesshours.csv")
store_timezones_df = pd.read_csv("static/storetimezones.csv")
store_timezones_dict = dict(
    zip(store_timezones_df["store_id"], store_timezones_df["timezone_str"])
)

with app.app_context():
    db.create_all()
    # TO POPULATE THE TABLES
    # Populate StoreStatus table
    for index, row in store_status_df.iterrows():
        timestamp_obj = datetime.strptime(
            row["timestamp_utc"], "%Y-%m-%d %H:%M:%S.%f %Z"
        )
        # Convert the datetime object to Unix epoch time in seconds
        epoch_time = int(timestamp_obj.timestamp())
        store_status = StoreStatus(
            store_id=row["store_id"], timestamp_utc=epoch_time, status=row["status"]
        )
        db.session.add(store_status)

    # Populate BusinessHours table
    for index, row in business_hours_df.iterrows():
        store_id = row["store_id"]
        day_of_week = row["day"]
        start_time_local = row["start_time_local"]
        end_time_local = row["end_time_local"]
        # Retrieve the store's timezone from the dictionary
        store_timezone_str = store_timezones_dict.get(store_id)

        if not store_timezone_str:
            store_timezone_str = "America/Chicago"
        store_timezone = pytz.timezone(store_timezone_str)

        # Convert start and end times to epoch
        utc_epoch_time = time_to_epoch("00:00:00", pytz.timezone("UTC"))
        start_time_epoch = (
            time_to_epoch(start_time_local, store_timezone) - utc_epoch_time
        )
        end_time_epoch = time_to_epoch(end_time_local, store_timezone) - utc_epoch_time

        # Create a BusinessHours entry with UTC and epoch times
        business_hours = BusinessHours(
            store_id=store_id,
            day_of_week=day_of_week,
            start_time_utc=start_time_epoch,
            end_time_utc=end_time_epoch,
        )

        db.session.add(business_hours)

    # Populate StoreTimezones table
    for index, row in store_timezones_df.iterrows():
        store_timezone = StoreTimezones(
            store_id=row["store_id"], timezone_str=row["timezone_str"]
        )
        db.session.add(store_timezone)

    # Commit the changes to the database
    db.session.commit()

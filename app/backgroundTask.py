from app.helper import *

def background_task(**kwargs) -> None:
    current_time = kwargs["current_time"]
    report_id = kwargs["report_id"]

    # Get all the store ids data of all timestamps
    store_ids_data = get_store_ids_data()
    # keep a dict of all the unique store ids, this represents a dict of all the stores
    unique_store_ids = {x[0] for x in store_ids_data}
    # Get a list of operational business hours for each weekday for all stores
    business_hours_data = get_business_hours_data()
    # Store all the operational business hours for every store in a dict format for fast retrieval
    business_hours_hash = get_business_hours_hash(business_hours_data, unique_store_ids)
    # For every store, create a list of time intervals when it was expected to be active, roughtly during the last 7 days
    expected_active_intervals = get_expected_active_intervals(business_hours_hash, unique_store_ids, current_time)
    # generate the report data and store it into the database
    generate_report(report_id, store_ids_data, expected_active_intervals, current_time)
    print(f"thread task completed for report id {report_id}")


from datetime import datetime, timedelta
from ryanair import Ryanair
import time

api = Ryanair(currency="EUR")  # Euro currency, so could also be GBP etc. also

origin = "KUN"
max_price = 200
min_duration_days = 2  # New variable to adjust minimum duration in days

#trips = api.get_cheapest_return_flights(origin, from_date, from_date + timedelta(days=delta), to_date, to_date + timedelta(days=delta))

period_start = datetime.strptime("2025-01-01", '%Y-%m-%d') #first date to check, it will check all flights starting from the same weekday
period_end = datetime.strptime("2025-09-30", '%Y-%m-%d')
from_date = period_start

# List of Lithuanian public holidays in 2024
public_holidays = [
    "2024-01-01", "2024-02-16", "2024-03-11", "2024-04-01", "2024-05-01",
    "2024-06-24", "2024-07-06", "2024-08-15", "2024-11-01", "2024-12-25",
    "2024-12-26",
    "2025-01-01", "2025-02-16", "2025-03-11", "2025-04-21", "2025-05-01",
    "2025-06-24", "2025-07-06", "2025-08-15", "2025-11-01", "2025-12-25",
    "2025-12-26"
]
public_holidays = [datetime.strptime(date, '%Y-%m-%d') for date in public_holidays]

def count_weekdays(start_date, end_date, outbound_time, inbound_time):
    weekdays = 0
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() < 5 and current_date not in public_holidays:  # Monday to Friday and not a public holiday
            if not (current_date == start_date and outbound_time.hour >= 17) and not (current_date == end_date and inbound_time.hour <= 10):
                weekdays += 1
        current_date += timedelta(days=1)
    return weekdays

while from_date < period_end:
    print()
    to_date = from_date + timedelta(days=3)
    print("Checking weekend: {} => {} ".format(from_date.date(), from_date.date() + timedelta(days=4)))
    trips = api.get_cheapest_return_flights(origin, from_date, from_date + timedelta(days=3), to_date, to_date + timedelta(days=1))

    for trip in trips:
        duration_seconds = (trip.inbound.departureTime - trip.outbound.departureTime).total_seconds()
        duration_days = int(duration_seconds // 86400)
        duration_hours = int((duration_seconds % 86400) // 3600)
        if trip.totalPrice <= max_price and duration_days >= min_duration_days:  # Filter trips based on max_price and duration
            weekdays_used = count_weekdays(trip.outbound.departureTime, trip.inbound.departureTime, trip.outbound.departureTime, trip.inbound.departureTime)
            print ("{} => {} {} {}€ ({} days, {} hours, {} weekdays)".format(origin, trip.outbound.destination, trip.outbound.destinationFull, round(trip.totalPrice), duration_days, duration_hours, weekdays_used))
            print("{} [{}] || [{}] {} ". format(trip.outbound.departureTime.strftime('%Y-%m-%d %H:%M'), trip.outbound.departureTime.strftime('%a'), trip.inbound.departureTime.strftime('%a'), trip.inbound.departureTime.strftime('%Y-%m-%d %H:%M')))
            print()
    from_date = from_date + timedelta(7)
    time.sleep(1)
    print("====================")

from datetime import datetime, timedelta
from ryanair import Ryanair

api = Ryanair(currency="EUR")  # Euro currency, so could also be GBP etc. also


from_date = datetime.strptime("2024-09-26", '%Y-%m-%d')
to_date = datetime.strptime("2024-10-13", '%Y-%m-%d')

origin = "KUN"

min_trip_duration = 7  # Define the minimum desired trip duration in days
max_trip_duration = 10  # Define the maximum desired trip duration in days

all_trips = []

# Iterate over possible start dates within the range
current_date = from_date
while current_date <= to_date - timedelta(days=min_trip_duration):
    for duration in range(min_trip_duration, max_trip_duration + 1):
        return_date = current_date + timedelta(days=duration)
        if return_date > to_date:
            break
            
        trips = api.get_cheapest_return_flights(origin, current_date, current_date, return_date, return_date)
        
        # Filter trips based on the desired trip duration
        for trip in trips:
            trip_duration = (trip.inbound.departureTime - trip.outbound.departureTime).days
            if min_trip_duration <= trip_duration <= max_trip_duration:
                all_trips.append(trip)
    
    current_date += timedelta(days=1)

# Variable to determine sorting preference
sort_by_price = True  # Set to False to sort by date

# Print all trips found
if all_trips:
    # Sort trips based on the flag
    if sort_by_price:
        all_trips.sort(key=lambda trip: trip.totalPrice)
    else:
        all_trips.sort(key=lambda trip: trip.outbound.departureTime)
    
    for trip in all_trips:
        duration_seconds = (trip.inbound.departureTime - trip.outbound.departureTime).total_seconds()
        duration_days = int(duration_seconds // 86400)
        duration_hours = int((duration_seconds % 86400) // 3600)
        weekdays_used = (trip.inbound.departureTime - trip.outbound.departureTime).days - (trip.inbound.departureTime - trip.outbound.departureTime).days // 7 * 2
        print("{} => {} {} {}€ ({} days, {} hours, {} weekdays)".format(origin, trip.outbound.destination, trip.outbound.destinationFull, round(trip.totalPrice), duration_days, duration_hours, weekdays_used))
        print("{} [{}] || [{}] {} ".format(trip.outbound.departureTime.strftime('%Y-%m-%d %H:%M'), trip.outbound.departureTime.strftime('%a'), trip.inbound.departureTime.strftime('%a'), trip.inbound.departureTime.strftime('%Y-%m-%d %H:%M')))
        print()
else:
    print("No trips found for the desired duration.")

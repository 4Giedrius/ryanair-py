from datetime import datetime, timedelta
from ryanair import Ryanair
import time

api = Ryanair(currency="EUR")  # Euro currency, so could also be GBP etc. also



# Update origin to use airports from Lithuania
origin_airports = api.get_airports_by_country('LT', exclude_airports=['PLQ'])  # Get all Lithuanian airports
origin = origin_airports[0]  # Using first airport, or you could loop through all


#trips = api.get_cheapest_return_flights(origin, from_date, from_date + timedelta(days=delta), to_date, to_date + timedelta(days=delta))

period_start = datetime.strptime("2025-04-02", '%Y-%m-%d') #first date to check, it will check all flights starting from the same weekday
period_end = datetime.strptime("2025-04-30", '%Y-%m-%d')
from_date = period_start

# List of Lithuanian public holidays in 2024
public_holidays = [
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

def search_flights(origin_country: str, destinations: list = None, max_price: int = 200, min_duration_days: int = 2):
    """
    Search for flights from origin country to multiple destinations
    Args:
        origin_country (str): Country code for origin airports
        destinations (list): Optional list of destination country codes (can be either country codes or airport codes)
        max_price (int): Maximum price for flights
        min_duration_days (int): Minimum duration of the trip in days
    """
    origin_airports = api.get_airports_by_country(origin_country)
    
    # Check if destinations are provided
    destination_airports = []
    if destinations:
        for destination in destinations:
            if len(destination) == 2:  # Country code
                destination_airports.extend(api.get_airports_by_country(destination))
            else:  # Airport code
                destination_airports.append(destination)
    
    period_start = datetime.strptime("2025-04-01", '%Y-%m-%d')
    period_end = datetime.strptime("2025-05-30", '%Y-%m-%d')
    from_date = period_start
    
    while from_date < period_end:
        outbound_end = from_date + timedelta(days=3) #3 days outbound window
        return_start = from_date + timedelta(days=min_duration_days) #return start date based on min duration
        return_end = return_start + timedelta(days=5) #5 days return window
        
        all_weekend_trips = []  # Collect all trips for this weekend
        
        for origin in origin_airports:
            trips = api.get_cheapest_return_flights(
                origin, 
                from_date, outbound_end,
                return_start, return_end
            )
            
            for trip in trips:
                # Check if destination is in the list of valid destinations
                if destination_airports and trip.outbound.destination not in destination_airports:
                    continue
                
                duration_seconds = (trip.inbound.departureTime - trip.outbound.departureTime).total_seconds()
                duration_days = int(duration_seconds // 86400)
                duration_hours = int((duration_seconds % 86400) // 3600)
                
                if trip.totalPrice <= max_price and duration_days >= min_duration_days:
                    weekdays_used = count_weekdays(
                        trip.outbound.departureTime, 
                        trip.inbound.departureTime,
                        trip.outbound.departureTime,
                        trip.inbound.departureTime
                    )
                    # Calculate ratio of total days to weekdays used
                    ratio = duration_days / weekdays_used if weekdays_used > 0 else 0
                    all_weekend_trips.append((trip, duration_days, duration_hours, weekdays_used, ratio))
        
        if all_weekend_trips:
            print(f"Checking weekend: {from_date.date()} => {return_end.date()}")
            #print(f"Outbound start: {from_date.date()}, outbound end: {outbound_end.date()}, Return start: {return_start.date()}, Return end: {return_end.date()}")
            # Sort all trips for this weekend by price
            all_weekend_trips.sort(key=lambda x: x[0].totalPrice)
            
            for trip, duration_days, duration_hours, weekdays_used, ratio in all_weekend_trips:
                # Add stars for exceptional ratios
                stars = ''
                if ratio >= 4:
                    stars = ' ⭐⭐⭐'  # 4+ days per weekday
                elif ratio >= 3:
                    stars = ' ⭐⭐'    # 3+ days per weekday
                elif ratio >= 2:
                    stars = ' ⭐'      # 2+ days per weekday
                
                print(f"{trip.outbound.origin} => {trip.outbound.destination} {trip.outbound.destinationFull} {round(trip.totalPrice)}€ "
                      f"({duration_days} days, {duration_hours} hours, {weekdays_used} weekdays, ratio: {ratio:.1f}){stars}")
                print(f"{trip.outbound.departureTime.strftime('%Y-%m-%d %H:%M')} [{trip.outbound.departureTime.strftime('%a')}] || "
                      f"[{trip.inbound.departureTime.strftime('%a')}] {trip.inbound.departureTime.strftime('%Y-%m-%d %H:%M')}")
                print()
        
        from_date = from_date + timedelta(days=7)
        time.sleep(1)
        print("====================")

# Example usage:
if __name__ == "__main__":
    
    search_flights('LT', ['IT', 'ES'], max_price=250, min_duration_days=3)

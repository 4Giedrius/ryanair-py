from datetime import datetime, timedelta
from ryanair import Ryanair
import time

api = Ryanair(currency="EUR")  # Euro currency, so could also be GBP etc. also

# Hardcoded list of Lithuanian public holidays for 2025
public_holidays = [
    "2025-01-01", "2025-02-16", "2025-03-11", "2025-04-21", "2025-05-01",
    "2025-06-24", "2025-07-06", "2025-08-15", "2025-11-01", "2025-12-25",
    "2025-12-26"
]
public_holidays = [datetime.strptime(date, '%Y-%m-%d').date() for date in public_holidays]


def count_weekdays(start_date, end_date, outbound_time, inbound_time):
    """
    Count weekdays between start_date and end_date, excluding public holidays
    and considering flight times.
    """
    weekdays = 0
    
    # Convert datetime to date for start if it's not already
    current_date = start_date.date() if isinstance(start_date, datetime) else start_date
    # Convert datetime to date for end if it's not already
    end_date = end_date.date() if isinstance(end_date, datetime) else end_date
    
    while current_date <= end_date:
        is_weekday = current_date.weekday() < 5
        is_holiday = current_date in public_holidays
        is_first_day = current_date == start_date.date() if isinstance(start_date, datetime) else current_date == start_date
        is_last_day = current_date == end_date.date() if isinstance(end_date, datetime) else current_date == end_date
        
        # Count the day if:
        # 1. It's a weekday AND
        # 2. It's not a public holiday AND
        # 3. If it's the first day, the flight departs before 5 PM
        if is_weekday and not is_holiday:
            if is_first_day:
                outbound_datetime = outbound_time if isinstance(outbound_time, datetime) else datetime.combine(current_date, outbound_time)
                if outbound_datetime.hour < 17:  # Only count if departure is before 5 PM
                    weekdays += 1
            # elif is_last_day:
            #     inbound_datetime = inbound_time if isinstance(inbound_time, datetime) else datetime.combine(current_date, inbound_time)
            #     if inbound_datetime.hour >= 9:  # Only count if arrival is after 9 AM
            #         weekdays += 1
            else:
                weekdays += 1
                
        current_date += timedelta(days=1)
    
    return weekdays

def search_flights(origin_country: str, destinations: list = None, max_price: int = 200, min_duration_days: int = 2, max_duration_days: int = 7, start_date: str = "2025-04-01", end_date: str = "2025-05-30"):
    """
    Search for flights from origin country to multiple destinations
    Args:
        origin_country (str): Country code for origin airports
        destinations (list): Optional list of destination country codes (can be either country codes or airport codes)
        max_price (int): Maximum price for flights
        min_duration_days (int): Minimum duration of the trip in days
        max_duration_days (int): Maximum duration of the trip in days
        start_date (str): Start date for the search in 'YYYY-MM-DD' format
        end_date (str): End date for the search in 'YYYY-MM-DD' format
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
    
    period_start = datetime.strptime(start_date, '%Y-%m-%d')
    period_end = datetime.strptime(end_date, '%Y-%m-%d')
    from_date = period_start

    while from_date < period_end:
        outbound_end = from_date + timedelta(days=2)  # 3 days outbound window
        return_start = from_date + timedelta(days=min_duration_days)  # return start date based on min duration
        return_end = return_start + timedelta(days=5)  # 5 days return window
        
        all_weekend_trips = []  # Collect all trips for this weekend
        
        for origin in origin_airports:
            trips = api.get_cheapest_return_flights(
                origin, 
                from_date, outbound_end,
                return_start, return_end
            )
            
            for trip in trips:
                # Check if destination is in the list of valid destinations
                if destinations:
                    if trip.outbound.destination not in destination_airports:
                        continue
                
                duration_seconds = (trip.inbound.departureTime - trip.outbound.departureTime).total_seconds()
                duration_days = int(duration_seconds // 86400)
                duration_hours = int((duration_seconds % 86400) // 3600)
                
                # Check if the trip meets the duration criteria
                if trip.totalPrice <= max_price and duration_days >= min_duration_days and duration_days <= max_duration_days:
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
            # Sort all trips for this weekend by price
            all_weekend_trips.sort(key=lambda x: x[0].totalPrice)
            
            for trip, duration_days, duration_hours, weekdays_used, ratio in all_weekend_trips:
                # Add stars for exceptional ratios
                stars = ''
                if ratio >= 3:
                    stars = ' ⭐⭐⭐'  # 4+ days per weekday
                elif ratio >= 2:
                    stars = ' ⭐⭐'    # 3+ days per weekday
                elif ratio >= 1.5:
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
    search_flights(origin_country='LT', destinations=['CY', 'MT', 'GR'], max_price=250, min_duration_days=2, max_duration_days=5, start_date="2025-02-27", end_date="2025-10-01")
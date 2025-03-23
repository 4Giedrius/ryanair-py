from datetime import datetime, timedelta
from airbaltic import AirBaltic
import time
import logging
import concurrent.futures

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d %(levelname)s:%(message)s",
    datefmt="%Y-%m-%d %I:%M:%S",
    filename="airbaltic_weekends.log"
)
logger = logging.getLogger("airbaltic_weekendsearch")

# Initialize AirBaltic API
api = AirBaltic(currency="EUR")

# Hardcoded list of Lithuanian public holidays for 2025
public_holidays = [
    "2025-01-01", "2025-02-16", "2025-03-11", "2025-04-21", "2025-05-01",
    "2025-06-24", "2025-07-06", "2025-08-15", "2025-11-01", "2025-12-25",
    "2025-12-26"
]
public_holidays = [datetime.strptime(date, '%Y-%m-%d').date() for date in public_holidays]


def count_weekdays(start_date, end_date):
    """
    Count weekdays between start_date and end_date, excluding public holidays.
    """
    weekdays = 0
    
    # Convert datetime to date for start if it's not already
    current_date = start_date.date() if isinstance(start_date, datetime) else start_date
    # Convert datetime to date for end if it's not already
    end_date = end_date.date() if isinstance(end_date, datetime) else end_date
    
    while current_date <= end_date:
        is_weekday = current_date.weekday() < 5  # Monday to Friday
        is_holiday = current_date in public_holidays
        
        # Count the day if it's a weekday and not a public holiday
        if is_weekday and not is_holiday:
            weekdays += 1
                
        current_date += timedelta(days=1)
    
    return weekdays


def search_weekend_flights(
    origin: str, 
    destinations: list = None, 
    max_price: int = 200, 
    min_duration_days: int = 2, 
    max_duration_days: int = 7, 
    start_date: str = "2025-04-01", 
    end_date: str = "2025-05-30"
):
    """
    Search for weekend flights from origin to multiple destinations
    
    Args:
        origin (str): Origin airport code (e.g., 'VNO')
        destinations (list): Optional list of destination airport codes
        max_price (int): Maximum price for flights
        min_duration_days (int): Minimum duration of the trip in days
        max_duration_days (int): Maximum duration of the trip in days
        start_date (str): Start date for the search in 'YYYY-MM-DD' format
        end_date (str): End date for the search in 'YYYY-MM-DD' format
    """
    period_start = datetime.strptime(start_date, '%Y-%m-%d')
    period_end = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Start from the first Thursday in the period
    from_date = period_start
    while from_date.weekday() != 3:  # Thursday is 3
        from_date += timedelta(days=1)
        if from_date >= period_end:
            logger.warning("No Thursdays found in the specified period")
            return

    # First, get all available destinations if not specified
    if destinations is None:
        try:
            print("Fetching available destinations...")
            destinations = api.get_available_destinations(
                origin, 
                period_start, 
                period_end
            )
            print(f"Found {len(destinations)} available destinations")
        except Exception as e:
            logger.error(f"Error fetching available destinations: {e}")
            print(f"Error fetching available destinations: {e}")
            return

    while from_date < period_end:
        # Define weekend search window: Thursday to Monday
        outbound_start = from_date  # Thursday
        outbound_end = from_date + timedelta(days=1)  # Friday
        
        # Return window: Sunday to Tuesday
        return_start = from_date + timedelta(days=3)  # Sunday
        return_end = from_date + timedelta(days=5)  # Tuesday
        
        logger.info(f"Searching weekend: {outbound_start.date()} to {return_end.date()}")
        print(f"Searching weekend: {outbound_start.date()} to {return_end.date()}")
        
        all_weekend_trips = []
        
        # Define all date combinations to search
        date_combinations = []
        
        # Thursday departures
        current_outbound = outbound_start
        while current_outbound <= outbound_end:
            current_return = return_start
            while current_return <= return_end:
                duration_days = (current_return - current_outbound).days
                if min_duration_days <= duration_days <= max_duration_days:
                    date_combinations.append((current_outbound, current_return))
                current_return += timedelta(days=1)
            current_outbound += timedelta(days=1)
        
        # Use ThreadPoolExecutor for parallel requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Create a dictionary to store futures
            future_to_dates = {}
            
            # Submit tasks for each destination and date combination
            for destination in destinations:
                for outbound_date, return_date in date_combinations:
                    future = executor.submit(
                        search_single_flight,
                        origin,
                        destination,
                        outbound_date,
                        return_date,
                        max_price
                    )
                    future_to_dates[future] = (destination, outbound_date, return_date)
            
            # Process completed futures
            for future in concurrent.futures.as_completed(future_to_dates):
                destination, outbound_date, return_date = future_to_dates[future]
                try:
                    result = future.result()
                    if result:
                        all_weekend_trips.append(result)
                except Exception as e:
                    # Log error but continue with other destinations
                    logger.debug(f"Error searching {destination} for {outbound_date} to {return_date}: {e}")
        
        # Display results for this weekend
        if all_weekend_trips:
            # Sort by price
            all_weekend_trips.sort(key=lambda x: x["price"])
            
            print(f"Results for weekend {outbound_start.date()} to {return_end.date()}:")
            for trip in all_weekend_trips:
                departure_date = datetime.strptime(trip["departure_date"], "%Y-%m-%d")
                return_date = datetime.strptime(trip["return_date"], "%Y-%m-%d")
                
                duration_days = (return_date - departure_date).days
                weekdays_used = count_weekdays(departure_date, return_date)
                
                # Calculate ratio of total days to weekdays used
                ratio = duration_days / weekdays_used if weekdays_used > 0 else 0
                
                # Add stars for exceptional ratios
                stars = ''
                if ratio >= 3:
                    stars = ' ⭐⭐⭐'  # 3+ days per weekday
                elif ratio >= 2:
                    stars = ' ⭐⭐'    # 2+ days per weekday
                elif ratio >= 1.5:
                    stars = ' ⭐'      # 1.5+ days per weekday
                
                print(f"{trip['origin']} => {trip['destination']} {round(trip['price'])}€ "
                      f"({duration_days} days, {weekdays_used} weekdays, ratio: {ratio:.1f}){stars}")
                print(f"{departure_date.strftime('%Y-%m-%d')} [{departure_date.strftime('%a')}] || "
                      f"[{return_date.strftime('%a')}] {return_date.strftime('%Y-%m-%d')}")
                print()
        else:
            print(f"No suitable flights found for weekend {outbound_start.date()} to {return_end.date()}")
        
        # Move to next Thursday
        from_date += timedelta(days=7)
        print("====================")


def search_single_flight(origin, destination, departure_date, return_date, max_price):
    """
    Search for a single flight with specific parameters
    """
    try:
        # Search flights for this specific date combination
        price_data = api.get_flight_price(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date
        )
        
        # Check if we have a price for this destination
        if destination in price_data:
            price = price_data[destination]
            
            # Apply price filter
            if max_price is None or price <= max_price:
                return {
                    "origin": origin,
                    "destination": destination,
                    "departure_date": api._format_date(departure_date),
                    "return_date": api._format_date(return_date),
                    "price": price,
                    "currency": api.currency
                }
    except Exception as e:
        # Don't log every 500 error, as these are expected for many destinations
        if "500 Server Error" in str(e):
            pass
        else:
            logger.warning(f"Error searching {origin} to {destination}: {e}")
    
    return None


# Example usage
if __name__ == "__main__":
    # You can specify destinations or leave as None to search all destinations
    destinations = ['RIX', 'TLL', 'ARN', 'CPH', 'OSL', 'HEL']  # Focus on nearby destinations that are more likely to have flights
    
    search_weekend_flights(
        origin='VNO',
        destinations=None,
        max_price=150,
        min_duration_days=2,
        max_duration_days=5,
        start_date="2025-06-13",
        end_date="2025-06-30"
    ) 
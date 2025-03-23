from datetime import datetime, timedelta, time
import time as time_module
import logging
import concurrent.futures
import sqlite3
from typing import List, Dict, Any, Union, Optional

# Import airline APIs
from ryanair import Ryanair
from airbaltic import AirBaltic

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d %(levelname)s:%(message)s",
    datefmt="%Y-%m-%d %I:%M:%S",
    filename="weekend_flights.log"
)
logger = logging.getLogger("weekend_flight_search")

# Hardcoded list of Lithuanian public holidays for 2025
public_holidays = [
    "2025-01-01", "2025-02-16", "2025-03-11", "2025-04-21", "2025-05-01",
    "2025-06-24", "2025-07-06", "2025-08-15", "2025-11-01", "2025-12-25",
    "2025-12-26"
]
public_holidays = [datetime.strptime(date, '%Y-%m-%d').date() for date in public_holidays]


class AirlineAPI:
    """Base class for airline APIs to standardize interfaces"""
    
    def __init__(self, currency="EUR"):
        self.currency = currency
        self.name = "Generic Airline"
    
    def search_flights(self, origin, destination, departure_date, return_date):
        """Search for flights between origin and destination on specific dates"""
        raise NotImplementedError("Each airline API must implement this method")
    
    def get_available_destinations(self, origin, start_date, end_date):
        """Get available destinations from origin within date range"""
        raise NotImplementedError("Each airline API must implement this method")


class RyanairAPI(AirlineAPI):
    """Adapter for Ryanair API"""
    
    def __init__(self, currency="EUR"):
        super().__init__(currency)
        self.api = Ryanair(currency=currency)
        self.name = "Ryanair"
    
    def search_flights(self, origin, destination, departure_date, return_date):
        """Search for flights between origin and destination on specific dates"""
        try:
            # For Ryanair, we need to use a date range for their API
            outbound_end = departure_date + timedelta(days=0)  # Same day
            return_end = return_date + timedelta(days=0)  # Same day
            
            trips = self.api.get_cheapest_return_flights(
                origin, 
                departure_date, outbound_end,
                return_date, return_end
            )
            
            results = []
            for trip in trips:
                if trip.outbound.destination == destination:
                    results.append({
                        "airline": self.name,
                        "origin": trip.outbound.origin,
                        "destination": trip.outbound.destination,
                        "departure_date": trip.outbound.departureTime.strftime("%Y-%m-%d"),
                        "departure_time": trip.outbound.departureTime.strftime("%H:%M"),
                        "return_date": trip.inbound.departureTime.strftime("%Y-%m-%d"),
                        "return_time": trip.inbound.departureTime.strftime("%H:%M"),
                        "price": trip.totalPrice,
                        "currency": self.currency,
                        "outbound_flight": trip.outbound.flightNumber,
                        "inbound_flight": trip.inbound.flightNumber,
                        "outbound_datetime": trip.outbound.departureTime,
                        "inbound_datetime": trip.inbound.departureTime
                    })
            return results
        except Exception as e:
            logger.warning(f"Error searching Ryanair flights from {origin} to {destination}: {e}")
            return []
    
    def get_available_destinations(self, origin, start_date, end_date):
        """Get available destinations from origin within date range"""
        # For Ryanair, we'll use their country-based airport lookup
        try:
            # This is a simplified approach - in a real implementation, you might
            # want to check actual available routes
            return self.api.get_airports_by_country("EU")  # Get all European airports
        except Exception as e:
            logger.warning(f"Error getting Ryanair destinations from {origin}: {e}")
            return []


class AirBalticAPI(AirlineAPI):
    """Adapter for AirBaltic API"""
    
    def __init__(self, currency="EUR"):
        super().__init__(currency)
        self.api = AirBaltic(currency=currency)
        self.name = "AirBaltic"
    
    def search_flights(self, origin, destination, departure_date, return_date):
        """Search for flights between origin and destination on specific dates"""
        try:
            price_data = self.api.get_flight_price(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                return_date=return_date
            )
            
            results = []
            if destination in price_data:
                price = price_data[destination]
                
                # AirBaltic API doesn't provide flight times, so we'll use placeholder times
                # In a real implementation, you would need to get the actual flight times
                results.append({
                    "airline": self.name,
                    "origin": origin,
                    "destination": destination,
                    "departure_date": self.api._format_date(departure_date),
                    "departure_time": "12:00",  # Placeholder
                    "return_date": self.api._format_date(return_date),
                    "return_time": "12:00",  # Placeholder
                    "price": price,
                    "currency": self.currency,
                    "outbound_flight": "BT???",  # Placeholder
                    "inbound_flight": "BT???",  # Placeholder
                    "outbound_datetime": datetime.combine(
                        departure_date if isinstance(departure_date, datetime) else 
                        datetime.strptime(departure_date, "%Y-%m-%d"), 
                        datetime.strptime("12:00", "%H:%M").time()
                    ),
                    "inbound_datetime": datetime.combine(
                        return_date if isinstance(return_date, datetime) else 
                        datetime.strptime(return_date, "%Y-%m-%d"), 
                        datetime.strptime("12:00", "%H:%M").time()
                    )
                })
            return results
        except Exception as e:
            logger.warning(f"Error searching AirBaltic flights from {origin} to {destination}: {e}")
            return []
    
    def get_available_destinations(self, origin, start_date, end_date):
        """Get available destinations from origin within date range"""
        try:
            return self.api.get_available_destinations(origin, start_date, end_date)
        except Exception as e:
            logger.warning(f"Error getting AirBaltic destinations from {origin}: {e}")
            return []


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
        is_first_day = current_date == start_date.date() if isinstance(start_date, datetime) else current_date == start_date
        is_last_day = current_date == end_date.date() if isinstance(end_date, datetime) else current_date == end_date
        
        # Count the day if:
        # 1. It's a weekday AND
        # 2. It's not a public holiday AND
        # 3. If it's the first day, the flight departs before 5 PM
        if is_weekday and not is_holiday:
            if is_first_day:
                # For the first day, only count if departure is before 5 PM
                if isinstance(start_date, datetime) and start_date.hour < 17:
                    weekdays += 1
            elif is_last_day:
                # For the last day, only count if arrival is after 9 AM
                if isinstance(end_date, datetime) and end_date.hour >= 9:
                    weekdays += 1
            else:
                weekdays += 1
                
        current_date += timedelta(days=1)
    
    return weekdays


def search_single_flight(airline_api, origin, destination, departure_date, return_date, max_price):
    """
    Search for a single flight with specific parameters
    """
    try:
        results = airline_api.search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date
        )
        
        # Filter by price
        if max_price is not None:
            results = [r for r in results if r["price"] <= max_price]
            
        return results
    except Exception as e:
        logger.warning(f"Error searching {airline_api.name} from {origin} to {destination}: {e}")
    
    return []


def search_mixed_flights(
    origin: str,
    destinations: List[str],
    outbound_date: datetime,
    return_date: datetime,
    airline_apis: List[AirlineAPI],
    max_price: Optional[int] = None
):
    """
    Search for mixed flights (outbound with one airline, return with another)
    """
    all_flights = []
    
    # Use ThreadPoolExecutor for parallel requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Create a dictionary to store futures
        future_to_params = {}
        
        # Submit tasks for each destination and airline
        for destination in destinations:
            for airline_api in airline_apis:
                future = executor.submit(
                    search_single_flight,
                    airline_api,
                    origin,
                    destination,
                    outbound_date,
                    return_date,
                    max_price
                )
                future_to_params[future] = (destination, airline_api.name)
        
        # Process completed futures
        for future in concurrent.futures.as_completed(future_to_params):
            destination, airline_name = future_to_params[future]
            try:
                results = future.result()
                all_flights.extend(results)
            except Exception as e:
                logger.warning(f"Error processing results for {airline_name} to {destination}: {e}")
    
    return all_flights


def find_mixed_trips(flights, max_price):
    """
    Find mixed trips (outbound with one airline, return with another)
    """
    mixed_trips = []
    
    # Group flights by destination
    flights_by_destination = {}
    for flight in flights:
        destination = flight["destination"]
        if destination not in flights_by_destination:
            flights_by_destination[destination] = []
        flights_by_destination[destination].append(flight)
    
    # For each destination, find all possible outbound and return combinations
    for destination, dest_flights in flights_by_destination.items():
        # Find all outbound flights
        outbound_flights = [f for f in dest_flights]
        
        # For each outbound flight, find compatible return flights
        for outbound in outbound_flights:
            outbound_datetime = outbound["outbound_datetime"]
            
            # Find return flights that depart after the outbound arrival
            return_flights = [
                f for f in dest_flights
                if f["inbound_datetime"] > outbound_datetime + timedelta(days=1)  # At least 1 day at destination
            ]
            
            for return_flight in return_flights:
                # Calculate total price
                total_price = outbound["price"] / 2 + return_flight["price"] / 2  # Assuming round-trip prices
                
                # Check if the total price is within budget
                if max_price is None or total_price <= max_price:
                    # Create a mixed trip
                    mixed_trip = {
                        "outbound_airline": outbound["airline"],
                        "return_airline": return_flight["airline"],
                        "origin": outbound["origin"],
                        "destination": outbound["destination"],
                        "outbound_date": outbound["departure_date"],
                        "outbound_time": outbound["departure_time"],
                        "return_date": return_flight["return_date"],
                        "return_time": return_flight["return_time"],
                        "total_price": total_price,
                        "currency": outbound["currency"],
                        "outbound_flight": outbound["outbound_flight"],
                        "return_flight": return_flight["inbound_flight"],
                        "outbound_datetime": outbound["outbound_datetime"],
                        "return_datetime": return_flight["inbound_datetime"]
                    }
                    
                    # Calculate trip metrics
                    duration = (return_flight["inbound_datetime"] - outbound["outbound_datetime"]).days
                    weekdays_used = count_weekdays(
                        outbound["outbound_datetime"],
                        return_flight["inbound_datetime"]
                    )
                    
                    # Add metrics to the trip
                    mixed_trip["duration_days"] = duration
                    mixed_trip["weekdays_used"] = weekdays_used
                    mixed_trip["ratio"] = duration / weekdays_used if weekdays_used > 0 else 0
                    
                    mixed_trips.append(mixed_trip)
    
    return mixed_trips


def search_weekend_flights(
    origin: str, 
    destinations: List[str] = None, 
    excluded_airports: List[str] = None,
    max_price: int = 200, 
    min_duration_days: int = 2, 
    max_duration_days: int = 7, 
    start_date: str = "2025-04-01", 
    end_date: str = "2025-05-30",
    airlines: List[str] = None,
    db_path: str = "weekend_flights.db"
):
    """
    Search for weekend flights from origin to multiple destinations across multiple airlines
    
    Args:
        origin (str): Origin airport code (e.g., 'VNO')
        destinations (list): Optional list of destination airport codes
        excluded_airports (list): Optional list of airport codes to exclude from search
        max_price (int): Maximum price for flights
        min_duration_days (int): Minimum duration of the trip in days
        max_duration_days (int): Maximum duration of the trip in days
        start_date (str): Start date for the search in 'YYYY-MM-DD' format
        end_date (str): End date for the search in 'YYYY-MM-DD' format
        airlines (list): List of airlines to search ('ryanair', 'airbaltic', or both if None)
        db_path (str): Path to SQLite database for caching results
    """
    # Initialize airline APIs
    airline_apis = []
    if airlines is None or 'ryanair' in airlines:
        airline_apis.append(RyanairAPI(currency="EUR"))
    if airlines is None or 'airbaltic' in airlines:
        airline_apis.append(AirBalticAPI(currency="EUR"))
    
    # Initialize database for caching
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables if they don't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS flights (
        id INTEGER PRIMARY KEY,
        airline TEXT,
        origin TEXT,
        destination TEXT,
        departure_date TEXT,
        departure_time TEXT,
        return_date TEXT,
        return_time TEXT,
        price REAL,
        currency TEXT,
        outbound_flight TEXT,
        inbound_flight TEXT,
        search_date TEXT,
        UNIQUE(airline, origin, destination, departure_date, return_date)
    )
    ''')
    conn.commit()
    
    period_start = datetime.strptime(start_date, '%Y-%m-%d')
    period_end = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Start from the first Thursday in the period
    from_date = period_start
    while from_date.weekday() != 3:  # Thursday is 3
        from_date += timedelta(days=1)
        if from_date >= period_end:
            logger.warning("No Thursdays found in the specified period")
            return

    # Initialize excluded airports set
    excluded_airports = set(excluded_airports or [])
    
    # If destinations not specified, get all available destinations
    if destinations is None:
        all_destinations = set()
        for api in airline_apis:
            try:
                api_destinations = api.get_available_destinations(origin, from_date, period_end)
                all_destinations.update(api_destinations)
            except Exception as e:
                logger.error(f"Error getting destinations from {api.name}: {e}")
        
        # Remove excluded airports from all_destinations
        all_destinations = all_destinations - excluded_airports
        destinations = list(all_destinations)
        print(f"Found {len(destinations)} available destinations (after excluding {len(excluded_airports)} airports)")
    else:
        # Remove excluded airports from specified destinations
        destinations = [d for d in destinations if d not in excluded_airports]
        if len(destinations) == 0:
            logger.warning("No destinations remaining after applying exclusions")
            return
        print(f"Searching {len(destinations)} destinations (after excluding {len(excluded_airports)} airports)")
    
    while from_date < period_end:
        # Define weekend search window: Thursday to Monday
        outbound_start = from_date  # Thursday
        outbound_end = from_date + timedelta(days=1)  # Friday
        
        # Return window: Sunday to Tuesday
        return_start = from_date + timedelta(days=3)  # Sunday
        return_end = from_date + timedelta(days=5)  # Tuesday
        
        logger.info(f"Searching weekend: {outbound_start.date()} to {return_end.date()}")
        print(f"Searching weekend: {outbound_start.date()} to {return_end.date()}")
        
        # Define all date combinations to search
        date_combinations = []
        
        # Thursday/Friday departures
        current_outbound = outbound_start
        while current_outbound <= outbound_end:
            current_return = return_start
            while current_return <= return_end:
                duration_days = (current_return - current_outbound).days
                if min_duration_days <= duration_days <= max_duration_days:
                    date_combinations.append((current_outbound, current_return))
                current_return += timedelta(days=1)
            current_outbound += timedelta(days=1)
        
        all_weekend_trips = []
        
        # Search for flights for each date combination
        for outbound_date, return_date in date_combinations:
            # Search for flights across all airlines
            flights = search_mixed_flights(
                origin=origin,
                destinations=destinations,
                outbound_date=outbound_date,
                return_date=return_date,
                airline_apis=airline_apis,
                max_price=max_price
            )
            
            # Cache results in database
            for flight in flights:
                try:
                    cursor.execute('''
                    INSERT OR REPLACE INTO flights 
                    (airline, origin, destination, departure_date, departure_time, 
                     return_date, return_time, price, currency, outbound_flight, 
                     inbound_flight, search_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        flight["airline"],
                        flight["origin"],
                        flight["destination"],
                        flight["departure_date"],
                        flight["departure_time"],
                        flight["return_date"],
                        flight["return_time"],
                        flight["price"],
                        flight["currency"],
                        flight["outbound_flight"],
                        flight["inbound_flight"],
                        datetime.now().strftime("%Y-%m-%d")
                    ))
                except Exception as e:
                    logger.error(f"Error caching flight: {e}")
            
            conn.commit()
            
            # Find mixed trips (outbound with one airline, return with another)
            mixed_trips = find_mixed_trips(flights, max_price)
            
            # Add all trips to results
            all_weekend_trips.extend(flights)
            all_weekend_trips.extend(mixed_trips)
        
        # Display results for this weekend
        if all_weekend_trips:
            # Sort by price
            all_weekend_trips.sort(key=lambda x: x.get("total_price", x.get("price", float("inf"))))
            
            print(f"Results for weekend {outbound_start.date()} to {return_end.date()}:")
            for trip in all_weekend_trips[:20]:  # Show top 20 results
                # Determine if this is a mixed trip
                is_mixed = "outbound_airline" in trip
                
                if is_mixed:
                    # Mixed trip (different airlines for outbound and return)
                    duration_days = trip["duration_days"]
                    weekdays_used = trip["weekdays_used"]
                    ratio = trip["ratio"]
                    price = trip["total_price"]
                    
                    # Add stars for exceptional ratios
                    stars = ''
                    if ratio >= 3:
                        stars = ' ⭐⭐⭐'  # 3+ days per weekday
                    elif ratio >= 2:
                        stars = ' ⭐⭐'    # 2+ days per weekday
                    elif ratio >= 1.5:
                        stars = ' ⭐'      # 1.5+ days per weekday
                    
                    print(f"MIXED: {trip['outbound_airline']} + {trip['return_airline']}")
                    print(f"{trip['origin']} => {trip['destination']} {round(price)}€ "
                          f"({duration_days} days, {weekdays_used} weekdays, ratio: {ratio:.1f}){stars}")
                    print(f"{trip['outbound_date']} {trip['outbound_time']} || "
                          f"{trip['return_date']} {trip['return_time']}")
                else:
                    # Single airline trip
                    outbound_datetime = trip["outbound_datetime"]
                    inbound_datetime = trip["inbound_datetime"]
                    
                    duration_days = (inbound_datetime - outbound_datetime).days
                    weekdays_used = count_weekdays(outbound_datetime, inbound_datetime)
                    
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
                    
                    print(f"{trip['airline']}: {trip['origin']} => {trip['destination']} {round(trip['price'])}€ "
                          f"({duration_days} days, {weekdays_used} weekdays, ratio: {ratio:.1f}){stars}")
                    print(f"{trip['departure_date']} {trip['departure_time']} || "
                          f"{trip['return_date']} {trip['return_time']}")
                
                print()
        else:
            print(f"No suitable flights found for weekend {outbound_start.date()} to {return_end.date()}")
        
        # Move to next Thursday
        from_date += timedelta(days=7)
        time_module.sleep(1)  # Avoid hitting API rate limits
        print("====================")
    
    # Close database connection
    conn.close()


# Example usage
if __name__ == "__main__":
    # You can specify destinations or leave as None to search all destinations
    destinations = None
    
    # Airports to exclude (e.g., airports with inconvenient connections or expensive ground transport)
    excluded_airports = ['RIX', 'ARN']  # Example: Excluding Paris Beauvais, Stockholm Nyköping, Frankfurt-Hahn
    
    search_weekend_flights(
        origin='VNO',
        destinations=destinations,
        excluded_airports=excluded_airports,
        max_price=150,
        min_duration_days=2,
        max_duration_days=5,
        start_date="2025-06-13",
        end_date="2025-06-30",
        airlines=['ryanair', 'airbaltic']  # Search both airlines
    ) 
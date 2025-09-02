from datetime import datetime, timedelta
from ryanair import Ryanair
import time
import sqlite3  # New import for SQLite

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
    and considering flight times. Enhanced for maximum weekend utilization.
    """
    weekdays = 0
    
    # Convert datetime to date for start if it's not already
    current_date = start_date.date() if isinstance(start_date, datetime) else start_date
    # Convert datetime to date for end if it's not already
    end_date_obj = end_date.date() if isinstance(end_date, datetime) else end_date
    
    while current_date <= end_date_obj:
        is_weekday = current_date.weekday() < 5
        is_holiday = current_date in public_holidays
        is_first_day = current_date == (start_date.date() if isinstance(start_date, datetime) else start_date)
        is_last_day = current_date == end_date_obj
        
        # Count the day if it's a weekday and not a holiday
        if is_weekday and not is_holiday:
            if is_first_day:
                # Enhanced departure time logic - more flexible for weekend optimization
                outbound_datetime = outbound_time if isinstance(outbound_time, datetime) else datetime.combine(current_date, outbound_time)
                departure_hour = outbound_datetime.hour
                is_wednesday = outbound_datetime.weekday() == 2  # Wednesday
                is_friday = outbound_datetime.weekday() == 4      # Friday
                
                # Enhanced logic: don't count weekdays for late departures
                # Friday: don't count if departure is after 5 PM (evening departure)
                # Wednesday: count if < 6 PM OR evening departure (>= 5 PM)
                # Other weekdays: count if < 6 PM
                if is_friday and departure_hour >= 17:  # Friday evening departure
                    # Don't count Friday as a work day if departing after 5 PM
                    pass
                elif is_wednesday and departure_hour >= 17:
                    weekdays += 1  # Wednesday evening departures still count
                elif departure_hour < 18:
                    weekdays += 1
            elif is_last_day:
                # Enhanced return time logic - optimize for weekend returns
                inbound_datetime = inbound_time if isinstance(inbound_time, datetime) else datetime.combine(current_date, inbound_time)
                arrival_hour = inbound_datetime.hour
                is_monday = inbound_datetime.weekday() == 0  # Monday
                is_sunday = inbound_datetime.weekday() == 6   # Sunday
                
                # Enhanced logic: don't count return days for weekend returns
                # Sunday: never count as a work day
                # Monday: don't count if arrival is before 9 AM (early morning return)
                # Other weekdays: count if arrival >= 8 AM
                if is_sunday:
                    # Sunday returns never count as work days
                    pass
                elif is_monday and arrival_hour < 9:
                    # Early Monday morning returns don't count as work days
                    pass
                elif arrival_hour >= 8:
                    weekdays += 1
            else:
                weekdays += 1
                
        current_date += timedelta(days=1)
    
    return weekdays

def find_optimal_long_weekends(start_date, end_date):
    """
    Identify optimal long weekend opportunities based on public holidays.
    Returns a list of date ranges that maximize vacation efficiency.
    """
    period_start = datetime.strptime(start_date, '%Y-%m-%d') if isinstance(start_date, str) else start_date
    period_end = datetime.strptime(end_date, '%Y-%m-%d') if isinstance(end_date, str) else end_date
    
    optimal_periods = []
    current_date = period_start
    
    while current_date < period_end:
        # Check for holidays in the upcoming week
        week_start = current_date - timedelta(days=current_date.weekday())
        week_end = week_start + timedelta(days=6)
        
        week_holidays = [h for h in public_holidays if week_start.date() <= h <= week_end.date()]
        
        if week_holidays:
            # Calculate the best departure/return dates for this holiday week
            holiday_weekdays = [datetime.combine(h, datetime.min.time()).weekday() for h in week_holidays]
            
            # Determine optimal strategy based on holiday placement
            if 0 in holiday_weekdays:  # Monday holiday
                departure_start = week_start + timedelta(days=4)  # Friday before
                return_end = week_start + timedelta(days=8)       # Tuesday after
                vacation_days_needed = 1  # Only Tuesday
            elif 4 in holiday_weekdays:  # Friday holiday
                departure_start = week_start + timedelta(days=3)  # Thursday
                return_end = week_start + timedelta(days=7)       # Monday after
                vacation_days_needed = 0  # No extra days needed
            else:  # Mid-week holiday
                departure_start = week_start + timedelta(days=3)  # Thursday
                return_end = week_start + timedelta(days=7)       # Monday after
                vacation_days_needed = 1  # One bridge day
            
            total_days = (return_end - departure_start).days
            efficiency_ratio = total_days / max(vacation_days_needed, 1)
            
            optimal_periods.append({
                'departure_start': departure_start,
                'return_end': return_end,
                'holidays': week_holidays,
                'vacation_days_needed': vacation_days_needed,
                'total_days': total_days,
                'efficiency_ratio': efficiency_ratio
            })
        
        current_date += timedelta(days=7)  # Move to next week
    
    # Sort by efficiency ratio (most efficient first)
    optimal_periods.sort(key=lambda x: x['efficiency_ratio'], reverse=True)
    return optimal_periods


def search_flights(
    origin_country: str, 
    destinations: list = None, 
    max_price: int = 200, 
    min_duration_days: int = 2, 
    max_duration_days: int = 7, 
    start_date: str = "2025-04-01", 
    end_date: str = "2025-05-30",
    outbound_start_weekday: int = 3,  # 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat, 7=Sun
    outbound_end_weekday: int = 5,    # 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat, 7=Sun
    inbound_start_weekday: int = 7,   # 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat, 7=Sun
    inbound_end_weekday: int = 2      # 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat, 7=Sun
):
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
        outbound_start_weekday (int): First allowed outbound weekday (1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat, 7=Sun)
        outbound_end_weekday (int): Last allowed outbound weekday (1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat, 7=Sun)
        inbound_start_weekday (int): First allowed inbound weekday (1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat, 7=Sun)
        inbound_end_weekday (int): Last allowed inbound weekday (1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat, 7=Sun)
    """
    #origin_airports = api.get_airports_by_country(origin_country)
    origin_airports = ['KUN', 'VNO']
    
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
    
    # Display weekday configuration with numbers for clarity
    weekday_names = ['', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']  # Index 0 unused, 1-7 for days
    print(f"📅 Weekend Configuration:")
    print(f"   Weekday Numbers: 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat, 7=Sun")
    print(f"   Outbound: {weekday_names[outbound_start_weekday]} to {weekday_names[outbound_end_weekday]} ({outbound_start_weekday}→{outbound_end_weekday})")
    print(f"   Inbound:  {weekday_names[inbound_start_weekday]} to {weekday_names[inbound_end_weekday]} ({inbound_start_weekday}→{inbound_end_weekday})")
    print("=" * 80)
    
    # Find and display optimal long weekend opportunities
    optimal_periods = find_optimal_long_weekends(start_date, end_date)
    if optimal_periods:
        print(f"🎯 Found {len(optimal_periods)} optimal long weekend opportunities:")
        for i, period in enumerate(optimal_periods[:3]):  # Show top 3
            holiday_names = [h.strftime('%b %d') for h in period['holidays']]
            print(f"{i+1}. {period['departure_start'].strftime('%b %d')} to {period['return_end'].strftime('%b %d')}: "
                  f"{period['total_days']} days, {period['vacation_days_needed']} vacation days needed, "
                  f"ratio: {period['efficiency_ratio']:.1f} (holidays: {', '.join(holiday_names)})")
        print("=" * 60)
    else:
        print("No major holidays found in this period for optimization.")
        print("=" * 60)
    
    from_date = period_start

    while from_date < period_end:
        # Check for holidays to optimize weekend windows
        week_start = from_date - timedelta(days=from_date.weekday())
        week_dates = [week_start + timedelta(days=i) for i in range(7)]
        week_holidays = [d for d in week_dates if d.date() in public_holidays]
        
        # Convert user weekday numbers (1-7) to Python weekday numbers (0-6)
        # User: 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat, 7=Sun
        # Python: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
        outbound_start_py = (outbound_start_weekday - 1) % 7
        outbound_end_py = (outbound_end_weekday - 1) % 7
        inbound_start_py = (inbound_start_weekday - 1) % 7  
        inbound_end_py = (inbound_end_weekday - 1) % 7
        
        # Calculate outbound window based on user-specified weekdays
        # Find the first occurrence of outbound_start_weekday in this week
        outbound_start = week_start + timedelta(days=outbound_start_py)
        outbound_end = week_start + timedelta(days=outbound_end_py)
        
        # Ensure outbound window is within the search period
        if outbound_start < from_date:
            outbound_start = from_date
        if outbound_end >= period_end:
            outbound_end = period_end - timedelta(days=1)
            
        # Calculate return window based on user-specified weekdays and duration
        base_return_start = outbound_start + timedelta(days=min_duration_days)
        
        # Find the appropriate return weekdays
        if inbound_start_py <= inbound_end_py:
            # Normal case: Sunday to Tuesday (6,0,1 in Python numbering)
            days_to_add_start = (inbound_start_py - base_return_start.weekday()) % 7
            days_to_add_end = (inbound_end_py - base_return_start.weekday()) % 7
        else:
            # Wrap-around case: Saturday to Monday (5,6,0 in Python numbering)
            days_to_add_start = (inbound_start_py - base_return_start.weekday()) % 7
            days_to_add_end = (inbound_end_py - base_return_start.weekday() + 7) % 7
            
        return_start = base_return_start + timedelta(days=days_to_add_start)
        return_end = base_return_start + timedelta(days=days_to_add_end)
        
        # Extend return window for holiday weeks
        if week_holidays:
            return_end += timedelta(days=2)  # Extended return window for holidays
        
        
        all_weekend_trips = []  # Collect all trips for this weekend
        
        for origin in origin_airports:
            trips = api.get_cheapest_return_flights(
                origin, 
                outbound_start, outbound_end,  # Use enhanced outbound window
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
                #if trip.totalPrice <= max_price and duration_days >= min_duration_days and duration_days <= max_duration_days:
                weekdays_used = count_weekdays(
                    trip.outbound.departureTime, 
                    trip.inbound.departureTime,
                    trip.outbound.departureTime,
                    trip.inbound.departureTime
                )
                # Calculate ratio of total days to weekdays used
                # If 0 weekdays used, this is a perfect weekend trip - assign high ratio
                if weekdays_used == 0:
                    ratio = float('inf') if duration_days > 0 else 0  # Perfect weekend efficiency
                else:
                    ratio = duration_days / weekdays_used
                all_weekend_trips.append((trip, duration_days, duration_hours, weekdays_used, ratio))
                
        if all_weekend_trips:
            print(f"Checking weekend: {from_date.date()} => {return_end.date()}")
            
            # Calculate efficiency scores for enhanced sorting
            enhanced_trips = []
            for trip, duration_days, duration_hours, weekdays_used, ratio in all_weekend_trips:
                # Handle infinite ratios for perfect weekend trips
                if ratio == float('inf'):
                    efficiency_score = 1000  # Very high score for perfect weekend trips
                else:
                    efficiency_score = ratio * 100 - (trip.totalPrice / 10)  # Efficiency minus price penalty
                enhanced_trips.append((trip, duration_days, duration_hours, weekdays_used, ratio, efficiency_score))
            
            # Sort by efficiency first, then by price for maximum weekend utilization
            enhanced_trips.sort(key=lambda x: (-x[5], x[0].totalPrice))  # -efficiency_score, then price
            
            for trip, duration_days, duration_hours, weekdays_used, ratio, efficiency_score in enhanced_trips:
                # Enhanced star system with better thresholds
                stars = ''
                if ratio == float('inf'):
                    stars = ' 🌟🌟🌟'  # Perfect weekend trip - no weekdays used!
                elif ratio >= 3:
                    stars = ' ⭐⭐⭐'  # 3+ days per weekday
                elif ratio >= 2.5:
                    stars = ' ⭐⭐⭐'  # 2.5+ days per weekday  
                elif ratio >= 2:
                    stars = ' ⭐⭐'    # 2+ days per weekday
                elif ratio >= 1.5:
                    stars = ' ⭐'      # 1.5+ days per weekday
                
                # Add efficiency indicators
                if ratio == float('inf'):
                    efficiency_indicator = "🚀💎"  # Perfect weekend trip indicator
                else:
                    efficiency_indicator = "🎯" if efficiency_score > 200 else "✨" if efficiency_score > 150 else ""
                
                # Format ratio display
                if ratio == float('inf'):
                    ratio_str = "∞"  # Infinity symbol for perfect trips
                else:
                    ratio_str = f"{ratio:.1f}"
                
                print(f"{trip.outbound.origin} => {trip.outbound.destination} {trip.outbound.destinationFull} {round(trip.totalPrice)}€ "
                      f"({duration_days} days, {duration_hours} hours, {weekdays_used} weekdays, ratio: {ratio_str}){stars} {efficiency_indicator}")
                print(f"{trip.outbound.departureTime.strftime('%Y-%m-%d %H:%M')} [{trip.outbound.departureTime.strftime('%a')}] || "
                      f"[{trip.inbound.departureTime.strftime('%a')}] {trip.inbound.departureTime.strftime('%Y-%m-%d %H:%M')}")
                print()
        
        from_date = week_start + timedelta(days=7)  # Move to next week properly
        time.sleep(1)
        print("====================")

# Example usage:
if __name__ == "__main__":
    #destinations = ['MT'] # Added more warm countries
    #destinations = ['ES', 'IT', 'GR', 'PT', 'CY', 'MT', 'HR', 'ME', 'AL', 'TR'] # Added more warm countries

    destinations = []
    search_flights(
        origin_country='LT',
        destinations=destinations,
        max_price=150,
        min_duration_days=2,
        max_duration_days=5,
        start_date="2025-09-02",
        end_date="2025-11-30",
        outbound_start_weekday=4,  # 3=Wed
        outbound_end_weekday=6,    # 5=Fri
        inbound_start_weekday=7,   # 7=Sun
        inbound_end_weekday=1      # 2=Tue
    )


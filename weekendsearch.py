from datetime import datetime, timedelta
from ryanair import Ryanair
import time

api = Ryanair(currency="EUR")  # Euro currency, so could also be GBP etc. also

origin = "KUN"

#trips = api.get_cheapest_return_flights(origin, from_date, from_date + timedelta(days=delta), to_date, to_date + timedelta(days=delta))

period_start = datetime.strptime("2024-05-09", '%Y-%m-%d')
period_end = datetime.strptime("2024-12-31", '%Y-%m-%d')
from_date = period_start

while from_date < period_end:
	print()
	to_date = from_date + timedelta(days=3)
	print("Checking weekend: {} => {} ".format(from_date.date(), from_date.date() + timedelta(days=4)))
	trips = api.get_cheapest_return_flights(origin, from_date, from_date + timedelta(days=3), to_date, to_date + + timedelta(days=1))

	for trip in trips:
		print ("{} => {} {} {}€".format(origin, trip.outbound.destination, trip.outbound.destinationFull, round(trip.totalPrice)))
		#print(origin +" => " + + " " + trip.outbound.destinationFull + "  "  + str(round(trip.totalPrice)) + "€ " )  # Trip(totalPrice=85.31, outbound=Flight(departureTime=datetime.datetime(2023, 3, 12, 7, 30), flightNumber='FR5437', price=49.84, currency='EUR', origin='DUB', originFull='Dublin, Ireland', destination='EMA', destinationFull='East Midlands, United Kingdom'), inbound=Flight(departureTime=datetime.datetime(2023, 3, 13, 7, 45), flightNumber='FR5438', price=35.47, origin='EMA', originFull='East Midlands, United Kingdom', destination='DUB', destinationFull='Dublin, Ireland'))
		print("{} [{}] || [{}] {} ". format(trip.outbound.departureTime, trip.outbound.departureTime.strftime('%a'), trip.inbound.departureTime.strftime('%a'), trip.inbound.departureTime))
		#print(str() + "[" + str(trip.outbound.departureTime.weekday()) + " => " + str(trip.inbound.departureTime) + " [ " )
		print()

	from_date = from_date + timedelta(7)
	time.sleep(1)
	print("====================")

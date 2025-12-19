import csv

def load_flights_from_csv(path: str):
    flights = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            flights.append(row)
    return flights

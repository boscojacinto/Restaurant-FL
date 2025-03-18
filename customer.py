import csv
import random

# Create the data
data = []
for id_num in range(1, 10001):  # 1 to 10000
    # Generate random number of restaurant values (1 to 5)
    num_restaurants = random.randint(1, 5)
    # Generate random restaurant IDs (0 to 113)
    restaurants = random.sample(range(0, 114), num_restaurants)
    # Convert to CSV string
    restaurant_str = ",".join(map(str, restaurants))
    # Generate random avg spend in steps of 100
    avg_spend = random.randint(1, 11) * 100
    
    # Create row
    row = {
        "ID": id_num,
        "Area": "Powai",
        "City": "Mumbai",
        "Restaurant": restaurant_str,
        "Avg Spend": avg_spend,
        "Food type": "Mughlai"
    }
    data.append(row)

# Write to CSV file
with open('restaurant_data.csv', 'w', newline='') as file:
    fieldnames = ["ID", "Area", "City", "Restaurant", "Avg Spend", "Food type"]
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    
    writer.writeheader()
    for row in data:
        writer.writerow(row)

print("CSV file 'restaurant_data.csv' has been created with 10,000 entries!")
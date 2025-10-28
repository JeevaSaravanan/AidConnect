import json
import random

def generate_available_items():
    """Generate a random list of available items"""
    possible_items = [
        f"{random.randint(20, 150)} Beds",
        f"{random.randint(10, 100)} medical_kits",
        f"{random.randint(100, 500)} water_bottles",
        f"{random.randint(50, 300)} food_kits",
        f"{random.randint(50, 200)} blankets",
        f"{random.randint(20, 100)} first_aid_supplies",
        f"{random.randint(30, 150)} hygiene_kits",
        f"{random.randint(25, 100)} flashlights",
        f"{random.randint(50, 200)} batteries",
        f"{random.randint(40, 150)} toiletries",
        f"{random.randint(30, 120)} clothing_sets",
        f"{random.randint(25, 100)} sleeping_bags"
    ]
    
    # Randomly select 3-6 items
    num_items = random.randint(3, 6)
    return random.sample(possible_items, num_items)

def generate_source_platform():
    """Generate a random source platform"""
    platforms = ["X", "Facebook"]
    return random.choice(platforms)

def generate_post_details(available_items):
    """Generate post details sentence from available items"""
    items_str = ", ".join(available_items)
    return f"Shelter has available items: {items_str}"

def process_jsonl_file(input_file, output_file):
    """Process the JSONL file and add synthetic data"""
    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        for line in infile:
            # Parse the JSON object
            shelter = json.loads(line.strip())
            
            # Remove requested_items
            if 'requested_items' in shelter:
                del shelter['requested_items']
            
            # Add synthetic data
            available_items = generate_available_items()
            shelter['available_items'] = available_items
            shelter['source_platform'] = generate_source_platform()
            shelter['post_details'] = generate_post_details(available_items)
            
            # Write back to file
            outfile.write(json.dumps(shelter) + '\n')

if __name__ == "__main__":
    input_file = "shelters_actual.jsonl"
    output_file = "shelters_actual_updated.jsonl"
    
    process_jsonl_file(input_file, output_file)
    print(f"✅ Successfully processed {input_file}")
    print(f"✅ Output saved to {output_file}")
    print("\nTo replace the original file, run:")
    print(f"  mv {output_file} {input_file}")

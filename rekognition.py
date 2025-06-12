import boto3
import csv
import argparse
import re
from difflib import SequenceMatcher

def load_team_roster(tsv_file):
    team_roster = []
    try:
        with open(tsv_file, 'r') as file:
            reader = csv.reader(file, delimiter='\t')
            for row in reader:
                code = row[0]
                match = re.match(r'-(\d+)-\s(.+)\s\((.+)\)', row[1])
                if match:
                    number = match.group(1)
                    name = match.group(2)
                    team = match.group(3)
                    player = {
                        "code": code,
                        "number": number,
                        "name": name,
                        "team": team,
                        "role": "Player"
                    }
                    team_roster.append(player)
    except FileNotFoundError:
        print(f"Error: The file {tsv_file} was not found.")
    except Exception as e:
        print(f"Error: {e}")
    return team_roster

def similar(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def get_person_bounding_boxes(photo_bytes):
    client = boto3.client('rekognition')
    response = client.detect_labels(Image={'Bytes': photo_bytes}, MaxLabels=20, MinConfidence=80)
    
    person_boxes = []
    for label in response['Labels']:
        if label['Name'] == 'Person':
            for instance in label.get('Instances', []):
                if 'BoundingBox' in instance:
                    person_boxes.append(instance['BoundingBox'])
    return person_boxes

def is_inside(box_small, box_large):
    # Determine if small box is fully inside the larger one
    s_left = box_small['Left']
    s_top = box_small['Top']
    s_right = s_left + box_small['Width']
    s_bottom = s_top + box_small['Height']

    l_left = box_large['Left']
    l_top = box_large['Top']
    l_right = l_left + box_large['Width']
    l_bottom = l_top + box_large['Height']

    return s_left >= l_left and s_right <= l_right and s_top >= l_top and s_bottom <= l_bottom

def detect_text(photo):
    detected_text = []

    client = boto3.client('rekognition')

    try:
        with open(photo, 'rb') as image:
            image_bytes = image.read()

        person_boxes = get_person_bounding_boxes(image_bytes)

        # Now detect text
        text_response = client.detect_text(Image={'Bytes': image_bytes})
        text_detections = text_response['TextDetections']

        for text in text_detections:
            if text['Type'] == 'LINE' and text['Confidence'] > 90.0:
                bounding_box = text['Geometry']['BoundingBox']
                
                # Accept only text inside at least one person box
                if any(is_inside(bounding_box, person_box) for person_box in person_boxes):
                    detected_text.append({
                        'text': text['DetectedText'],
                        'bounding_box': bounding_box
                    })

        return detected_text

    except FileNotFoundError:
        print(f"Error: The file {photo} was not found.")
        return []
    except boto3.exceptions.Boto3Error as e:
        print(f"Error: {e}")
        return []

def match_player_names_and_numbers(detected_text_items, team_roster):
    matched_players = []
    matched_player_codes = set()

    for item in detected_text_items:
        text = item['text']
        for player in team_roster:
            surname = player["name"].split()[-1]
            number = str(player["number"])

            if (text.lower() == surname.lower()) or \
               (text == number) or \
               (similar(text, surname) > 0.8) or \
               (similar(text, number) > 0.9):

                if player["code"] not in matched_player_codes:
                    matched_players.append(player)
                    matched_player_codes.add(player["code"])
    return matched_players

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detect player names and numbers from an image.")
    parser.add_argument("image", help="Path to the image file.")
    parser.add_argument("roster", help="Path to the TSV file containing the team roster.")

    args = parser.parse_args()

    team_roster = load_team_roster(args.roster)
    detected_text_items = detect_text(args.image)

    print("Detected player-region text:")
    for item in detected_text_items:
        print(f" - '{item['text']}' at {item['bounding_box']}")

    matched_players = match_player_names_and_numbers(detected_text_items, team_roster)

    print("\nMatched player names and numbers:")
    for player in matched_players:
        print(f"- Code: {player.get('code', 'N/A')}, Number: {player.get('number', 'N/A')}, Name: {player.get('name', 'N/A')}, Team: {player.get('team', 'N/A')}, Role: {player.get('role', 'Player')}")

import boto3
import csv
import argparse
import re

def load_team_roster(tsv_file):
    """
    Load the team roster from a TSV file.
    
    Parameters:
    tsv_file (str): Path to the TSV file containing the team roster.
    
    Returns:
    list: List of player dictionaries.
    """
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

def detect_text(photo):
    """
    Method to detect text in the given image.
    
    Parameters:
    photo (str): Path of the image.
    
    Returns:
    list: List of detected text lines with confidence greater than 90%.
    """

    detected_text = []

    # Initialize boto3 client
    client = boto3.client('rekognition')
    
    try:
        # Read image file
        with open(photo, 'rb') as image:
            response = client.detect_text(Image={'Bytes': image.read()})
        
        # Response from AWS Rekognition
        text_detections = response['TextDetections']
        for text in text_detections:
            if text['Type'] == 'LINE' and text['Confidence'] > 90.0:
                detected_text.append(text['DetectedText'])
        
        return detected_text
    
    except FileNotFoundError:
        print(f"Error: The file {photo} was not found.")
        return []
    except boto3.exceptions.Boto3Error as e:
        print(f"Error: {e}")
        return []

def match_player_names_and_numbers(detected_text, team_roster):
    """
    Method to match detected text against a team roster.
    
    Parameters:
    detected_text (list): List of detected text lines.
    team_roster (list): List of player dictionaries.
    
    Returns:
    list: List of matched player names and numbers with details.
    """
    matched_players = []
    matched_player_codes = set()

    for text in detected_text:
        for player in team_roster:
            surname = player["name"].split()[-1].lower()
            number = str(player["number"]).lower() if player["number"] else None
            if text.lower() == surname or (number and text.lower() == number):
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
    detected_text = detect_text(args.image)
    matched_players = match_player_names_and_numbers(detected_text, team_roster)
    
    print(f"Detected text: {detected_text}")
    print("Matched player names and numbers:")
    for player in matched_players:
        print(f"- Code: {player.get('code', 'N/A')}, Number: {player.get('number', 'N/A')}, Name: {player.get('name', 'N/A')}, Team: {player.get('team', 'N/A')}, Role: {player.get('role', 'Player')}")


botName='joeloswald-defbot'
import requests
import json
from random import sample, choice
from time import sleep
import pickle
import numpy as np

headers_vision = {'Ocp-Apim-Subscription-Key': 'YOUR_COMPUTER_VISION_KEY_HERE'}
vision_base_url = "https://ENTER_CORRECT_ENDPOINT/vision/v2.1/"
back_dict = dict()

analysed_tiles = []
previous_move = []
move_number = 0

# =============================================================================

def calculate_move(gamestate):
    global analysed_tiles
    global previous_move
    global move_number
    # Record the number of tiles so we know how many tiles we need to loop through
    num_tiles = len(gamestate["Board"])

    move_number += 1
    if gamestate["UpturnedTiles"] == []:
      print("{}. No upturned tiles for this move.".format(move_number))
    else:
      print("{}. ({}, {}) Upturned tiles for this move".format(move_number, gamestate["UpturnedTiles"][0]["Index"], gamestate["UpturnedTiles"][1]["Index"]))
    print("  gamestate: {}".format(gamestate))
      
    # If we have not yet used analysed_tiles (i.e. It is the first turn of the game)
    if analysed_tiles == []:
        # Create a list to hold tile information and set each one as UNANALYSED
        for index in range(num_tiles):
            # Mark tile as not analysed
            analysed_tiles.append({})
            analysed_tiles[index]["State"] = "UNANALYSED"
            analysed_tiles[index]["Subject"] = None
            analysed_tiles[index]["category"] = None
        get_categories(gamestate)

    if gamestate["UpturnedTiles"] != []:

        analyse_tiles(gamestate["UpturnedTiles"], gamestate)
        #conduct()
    else:
        # If it is not our first move of the game
        if previous_move != []:
            # then our previous move successfully matched two tiles
            # Update our analysed_tiles to mark the previous tiles as matched
            print("  MATCH: ({}, {}) - {}".format(previous_move[0], previous_move[1], analysed_tiles[previous_move[0]]["Subject"]))
            analysed_tiles[previous_move[0]]["State"] = "MATCHED"
            analysed_tiles[previous_move[1]]["State"] = "MATCHED"


    bonus_cat = gamestate['Bonus'].lower()
    

    if len(get_unanalysed_tiles()) == 0: #or move_number > 18:
        match = search_for_matching_tiles_category(bonus_cat)

    else:
        match = None
        
    if match is not None:
        # Print out the move for debugging ----------------->
        print("  Matching Move: {}".format(match))
        # Set our move to be these matching tiles
        move = match
    # If we don't have any matching tiles
    else:
        # Create a list of all the tiles that we haven't analysed yet
        unanalysed_tiles = get_unanalysed_tiles()
        # If there are some tiles that we haven't analysed yet
        if unanalysed_tiles != []:
            move = get_unequal_pair()
            print("  New tiles move: {}".format(move))
        # If the unanalysed_tiles list is empty (all tiles have been analysed)
        else:
            i = 0
            unmatched_tiles = get_unmatched_tiles()
            move = get_equal_pair()
            print("(Random) guess move: {}".format(move))

    # Store our move to look back at next turn
    previous_move = move
    # Return the move we wish to make
        
    return {"Tiles": move}


def get_unmatched_tiles():
    # Create a list of all the unmatched tiles
    unmatched_tiles = []
    # For every tile in the game
    for index, tile in enumerate(analysed_tiles):
        # If that tile hasn't been matched yet
        if tile["State"] != "MATCHED":
            # Add that tile to the list of unmatched tiles
            unmatched_tiles.append(index)
    # Return the list
    return unmatched_tiles


def get_unanalysed_tiles():
    # Filter out analysed tiles
    unanalysed_tiles = []
    # For every tile that hasn't been matched
    for index, tile in enumerate(analysed_tiles):
        # If the tile hasn't been analysed
        if tile["State"] == "UNANALYSED":
            unanalysed_tiles.append(index)
            
    return unanalysed_tiles

def analyse_tiles(tiles, gamestate):
    # For every tile in the list 'tiles'
    for tile in tiles:
        analyse_tile(tile, gamestate)

def analyse_tile(tile, gamestate):
    global known_pictures
    # If we have already analysed the tile
    if analysed_tiles[tile["Index"]]["State"] != "UNANALYSED":
        # We don't need to analyse the tile again, so stop
        return
    # Call analysis
    analyse_url = vision_base_url + "analyze"
    params_analyse = {'visualFeatures': 'categories,tags,description,faces,imageType,color,adult',
                      'details': 'celebrities,landmarks'}
    data = {"url": tile["Tile"]}
    msapi_response = microsoft_api_call(analyse_url, params_analyse, headers_vision, data)
    #print("  API Result tile #{}: {}".format(tile["Index"], msapi_response))        
    # Check if the subject of the tile is a landmark

    
    if analysed_tiles[tile["Index"]]["category"] == 'animals':
        subject = check_for_animal(msapi_response, gamestate["AnimalList"])
        
    elif analysed_tiles[tile["Index"]]["category"] == 'landmarks':
        subject = check_for_landmark(msapi_response)
        
    elif analysed_tiles[tile["Index"]]["category"] == 'words':
        subject = check_for_text(tile)
    print('Marked {} as {}'.format(tile['Index'], subject))   
    # Remember this tile by adding it to our list of known tiles
    # Mark that the tile has now been analysed

    analysed_tiles[tile["Index"]]["State"] = "ANALYSED"
    analysed_tiles[tile["Index"]]["Subject"] = subject
    #analysed_tiles[tile["Index"]]["category"] = cat


def check_for_animal(msapi_response, animal_list):
    # Initialise our subject to None
    subject = None
    # If the Microsoft API has returned a list of tags
    if "tags" in msapi_response:
        for tag in sorted(msapi_response["tags"], key=lambda x: x['confidence'], reverse=True):
            if "name" in tag and tag["name"] in animal_list:
                subject = tag["name"].lower()
                break
    return subject


# ----------------------------------- TODO -----------------------------------
def get_categories(gamestate):
    get_backs(gamestate['TileBacks'])
    for index, tile in enumerate(analysed_tiles):
        back = gamestate['TileBacks'][index]
        tile['category'] = back_dict[back]
   
          
def get_backs(back_list):
    analyse_url = vision_base_url + "ocr"
    params_analyse = {}
    for back in set(back_list):
        data = {"url": back}
        msapi_response = microsoft_api_call(analyse_url, params_analyse, headers_vision, data)
        back_dict[back] = msapi_response['regions'][0]['lines'][0]['words'][0]['text'].lower() + 's'
    
        
        
def get_unequal_pair():
    unanalysed_tiles = get_unanalysed_tiles()
    move = None
    for i in unanalysed_tiles:
        for j in unanalysed_tiles:
            if j <= i:
                continue
            print('for loop for not matching categories')
            if analysed_tiles[i]['category'] != analysed_tiles[j]['category']:
                move = [i,j]
                return move
                
    if move is None:
        print('Sampling because no unmatching tiles...')
        move = sample(unanalysed_tiles, 2)
    return move

def get_equal_pair():
    print('trying to match an equal pair, because no match found')
    unmatched_tiles = get_unmatched_tiles()
    move = None
    for i in unmatched_tiles:
        for j in unmatched_tiles:
            if j <= i:
                continue
            print('for loop for matching pairs')
            if i != j and analysed_tiles[i]['category'] == analysed_tiles[j]['category']:
                move = [i,j]
                return move
                
    if move is None:
        print('Sampling because no matching tiles...')
        move = sample(unmached_tiles, 2)
    return move
       
    

def check_for_landmark(msapi_response): # NOTE: you don't need a landmark_list
    subject = None

    for category in msapi_response["categories"]:
            # If the tag has a name and that name is one of the animals in our list
            if "detail" in category and "landmarks" in category["detail"] and category["detail"]["landmarks"]:
                # Record the name of the animal that is the subject of the tile
                # (We store the subject in lowercase to make comparisons easier)
                subject = category["detail"]["landmarks"][0]["name"].lower()
                # Print out the animal we have found here for debugging ----------------->
                print("  Landmark: {}".format(subject))
                # Exit the for loop
                break
    # Return the subject
    return subject


def check_for_text(tile):
    # Initialise our subject to None
    subject = None
    analyse_url = vision_base_url + "ocr"
    params_analyse = {}
    data = {"url": tile["Tile"]}
    msapi_response = microsoft_api_call(analyse_url, params_analyse, headers_vision, data)
    if msapi_response['regions'] != []:
        if "text" in msapi_response['regions'][0]['lines'][0]['words'][0]:
            subject = msapi_response['regions'][0]['lines'][0]['words'][0]['text'].lower()
    
    return subject


def search_for_matching_tiles():
    # For every tile subject and its index
    for index_1, tile_1 in enumerate(analysed_tiles):
        # Loop through every tile subject and index
        for index_2, tile_2 in enumerate(analysed_tiles):
            # If the two tile's subject is the same and isn't None and the tile
            # hasn't been matched before, and the tiles aren't the same tile
            if tile_1["State"] == tile_2["State"] == "ANALYSED" and tile_1["Subject"] == tile_2["Subject"] and tile_1["Subject"] is not None and index_1 != index_2:
                # Choose these two tiles
                # Return the two chosen tiles as a list
                return [index_1, index_2]
    # If we have not matched any tiles, return no matched tiles
    return None

def search_for_matching_tiles_category(category):
    print('Entering Search with category and following data: ')
    for i in get_unanalysed_tiles():
        print(analysed_tiles[i])
    print('Bonus category: ', category)
    for index_1, tile_1 in enumerate(analysed_tiles):
        # Loop through every tile subject and index
        for index_2, tile_2 in enumerate(analysed_tiles):
            # If the two tile's subject is the same and isn't None and the tile
            # hasn't been matched before, and the tiles aren't the same tile
            if tile_1["State"] == tile_2["State"] == "ANALYSED" and tile_1["Subject"] == tile_2["Subject"] and tile_1["Subject"] is not None and index_1 != index_2:
                if tile_1['category'] == tile_2['category'] == category: 
                    return [index_1, index_2]
    # If we have not matched any tiles, return no matched tiles
    print('NO PAIR FOR BONUS CATEGORY {}'.format(category))
    print('Enter normal match with: ', [analysed_tiles[a] for a in get_unmatched_tiles()])
    return search_for_matching_tiles()

#def conduct():
#    for category in ['words', 'animals', 'landmarks']:
#        ind = np.where((analysed_tiles['category'] == category) & ((analysed_tiles['State']='UNANALYSED') | (analysed_tiles['Subject'] is None)))
#        if len(ind) == 1:
#            subs, counts = np.unique([a['Subject'] for a in analysed_tiles], return_count = True)
#            analysed_tiles[ind]['State'] = 'ANALYSED'
#            analysed_tiles[ind]['Subject'] = subject

def microsoft_api_call(url, params, headers, data):
    # Make API request
    response = requests.post(url, params=params, headers=headers, json=data)
    # Convert result to JSON
    res = response.json()
    # While we have exceeded our request volume quota
    while "error" in res and res["error"]["code"] == "429":
        # Wait for 1 second
        sleep(1)
        # Print that we are retrying the API call here ----------------->
        print("Retrying")
        # Make API request
        response = requests.post(url, params=params, headers=headers, json=data)
        # Convert result to JSON
        res = response.json()
    # Print the result of the API call here for debugging ----------------->
    # print("  API Result: {}".format(res))
    # Return JSON result of API request
    return res

  
# Test the user's subscription key
#
# Raise an error if the user's API key is not valid for the Microsoft
# Computer Vision API call
def valid_subscription_key():
    # Make a computer vision api call
    test_api_call = microsoft_api_call(vision_base_url + "analyze", {}, headers_vision, {})
    
    if "error" in test_api_call:
        raise ValueError("Invalid Microsoft Computer Vision API key for current region: {}".format(test_api_call))


# Check the subscription key
valid_subscription_key()

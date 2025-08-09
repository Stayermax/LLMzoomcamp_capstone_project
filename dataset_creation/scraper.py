from apify_client import ApifyClient
from tqdm import tqdm
import json
import os
# Initialize the ApifyClient with your API token

actor_id = open("api_keys/actor_id", "r").read()
apify_key = open("api_keys/apify_key", "r").read()
client = ApifyClient(apify_key)

STYLES = [["Red"],["White"],["Rose"],["Sparkling"],["Dessert"],["Fortified"]]
PRICE_BINS = [(0,15),(15,30),(30,50),(50,100),(100,250)]
RATING_BINS = [[3, 4, 5], [1, 2]]
MIN_RATING = ["1", "3.2", "3.8", "4.2"]
SORTS = ["ratings_average", "ratings_count"]

run_input = {
  "allreviews": False,
  "discounts": False,
  "format": False,
  "keyword": "https://www.vivino.com/explore?e=eJwNycsNgCAUBMBu9owF7MFoB8az4achihAeGule5jqxcEAMNxWi_jioDrbxEViuy4zc_9j56hJ81RdScXReLJJpNF7qloM9BcJp_AG5TBmZ",
  "maximum": 200,
  "pricemax": 200,
  "pricemin": 0,
  "process": "ge",
  "proxy": {
    "useApifyProxy": True,
    "apifyProxyGroups": [
      "RESIDENTIAL"
    ]
  },
  "ratingmin": "",
  "reviewsfilter": [],
  "sortby": "",
  "summary": False,
  "winetypes": [
    "Red",
    "White",
    "Rose",
    "Sparkling",
    "Dessert",
    "Fortified"
  ],
  "market": "CA",
  "searchfilter": "",
  "grapetypes": "",
  "delay": 2,
  "retries": 3
}


def _run_actor(run_input: dict):
    # Run the Actor and wait for it to finish
    run = client.actor(actor_id).call(run_input=run_input)
    run_id = run["defaultDatasetId"]
    return run_id

def run_actor(style, pmin, pmax, rbin, sort_by, min_rating, results_max=100):
    run_input["winetypes"] = style
    run_input["pricemin"] = pmin
    run_input["pricemax"] = pmax
    run_input["reviewsfilter"] = rbin
    run_input["sortby"] = sort_by
    run_input["maximum"] = results_max
    run_input["ratingmin"] = min_rating
    
    file_name = f"data/scrapped_data/scrapped_data_{style[0]}_{pmin}_{pmax}_{sort_by}_{rbin}_{min_rating}.json"
    if os.path.exists(file_name):
        print(f"File {file_name} already exists")
        return
    print("Running actor for", style, pmin, pmax, rbin, sort_by, min_rating)

    run_id = _run_actor(run_input=run_input)
    
    res = []
    for item in client.dataset(run_id).iterate_items():
        res.append(item)
    json.dump(res, open(file_name, "w"))
    return res


def run_all(results_max=100):
    for sort_by in tqdm(SORTS):
        for rbin in tqdm(RATING_BINS):
            for (pmin,pmax) in tqdm(PRICE_BINS):
                for style in tqdm(STYLES):
                    if rbin == [3, 4, 5]:
                        for min_rating in tqdm(MIN_RATING):
                            print("Running actor for", style, pmin, pmax, rbin, sort_by, min_rating)
                            run_actor(
                                style=style, 
                                pmin=pmin, 
                                pmax=pmax, 
                                rbin=rbin, 
                                sort_by=sort_by, 
                                min_rating=min_rating
                            )
                    else:
                        run_actor(
                            style=style, 
                            pmin=pmin, 
                            pmax=pmax, 
                            rbin=rbin, 
                            sort_by=sort_by, 
                            min_rating="1"
                        )
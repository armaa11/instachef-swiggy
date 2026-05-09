import asyncio
import hashlib
from redis import Redis
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.config import settings

redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)

test_cases = [
    {
        "url": "https://www.youtube.com/watch?v=9WXinXCkJoI",
        "content": "Make dal tadka for 4 people. Need 200g toor dal, 2 tomatoes, 1 onion, 1 tsp cumin, 1 tsp turmeric, 1 tbsp ghee, salt to taste."
    },
    {
        "url": "https://www.youtube.com/watch?v=ANY_HEBBARS_SAMBAR_VIDEO",
        "content": "Sambar recipe. Ingredients: 1 cup toor dal, 2 tbsp tamarind, 1 tsp mustard seeds, 1 sprig curry leaves."
    },
    {
        "url": "Make dal tadka for 4 people. Need 200g toor dal, 2 tomatoes, 1 onion, 1 tsp cumin, 1 tsp turmeric, 1 tbsp ghee, salt to taste.",
        "content": "Make dal tadka for 4 people. Need 200g toor dal, 2 tomatoes, 1 onion, 1 tsp cumin, 1 tsp turmeric, 1 tbsp ghee, salt to taste."
    }
]

def seed_cache():
    print("Seeding demo cache...")
    for case in test_cases:
        cache_key = f"extract:{hashlib.sha256(case['url'].encode()).hexdigest()}"
        redis_client.setex(cache_key, 604800, case['content'])
        print(f"Seeded cache for {case['url'][:50]}...")
    print("Done!")

if __name__ == "__main__":
    seed_cache()

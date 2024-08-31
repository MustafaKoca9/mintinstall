import os
import threading
import json
import requests
import multiprocessing
from pathlib import Path
from gi.repository import GLib, GObject
from misc import print_timing

REVIEWS_CACHE = os.path.join(GLib.get_user_cache_dir(), "mintinstall", "reviews.json")

class Review:
    def __init__(self, packagename, date, username, rating, comment):
        self.date = date
        self.packagename = packagename
        self.username = username
        self.rating = int(rating)
        self.comment = comment

    @classmethod
    def from_json(cls, json_data: dict):
        return cls(**json_data)


class ReviewInfo:
    def __init__(self, name, score=0, avg_rating=0, num_reviews=0):
        self.name = name
        self.reviews = []
        self.categories = []
        self.score = score
        self.avg_rating = avg_rating
        self.num_reviews = num_reviews

    def update_stats(self):
        sum_rating = sum(review.rating for review in self.reviews)
        self.num_reviews = len(self.reviews)
        
        if self.num_reviews > 0:
            self.avg_rating = round(sum_rating / self.num_reviews, 1)
            significant_votes = min(10, self.num_reviews)
            missing_votes = 10 - significant_votes
            self.score = round((self.avg_rating * significant_votes + 2.5 * missing_votes) / 10, 1)
        else:
            self.score = 0

    @classmethod
    def from_json(cls, json_data: dict):
        reviews = [Review.from_json(review) for review in json_data.get("reviews", [])]
        instance = cls(json_data["name"], json_data["score"], json_data["avg_rating"], json_data["num_reviews"])
        instance.reviews = reviews
        return instance


class JsonObject:
    def __init__(self, cache, size):
        self.cache = cache
        self.size = int(size)

    @classmethod
    def from_json(cls, json_data: dict):
        cache = {key: ReviewInfo.from_json(info) for key, info in json_data["cache"].items()}
        return cls(cache, json_data["size"])


class ReviewCache(GObject.Object):
    __gsignals__ = {
        'reviews-updated': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    @print_timing
    def __init__(self):
        super().__init__()
        self._cache_lock = threading.Lock()
        self._reviews, self._size = self._load_cache()
        self.proc = None
        self._update_cache()

    def kill(self):
        if self.proc is not None:
            self.proc.terminate()
            self.proc = None

    def keys(self):
        with self._cache_lock:
            return list(self._reviews.keys())

    def values(self):
        with self._cache_lock:
            return list(self._reviews.values())

    def __getitem__(self, key):
        with self._cache_lock:
            return self._reviews.get(key, ReviewInfo(key))

    def __contains__(self, name):
        with self._cache_lock:
            return name in self._reviews

    def __len__(self):
        with self._cache_lock:
            return len(self._reviews)

    def _load_cache(self):
        path = Path(REVIEWS_CACHE)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open(mode='r', encoding="utf8") as f:
                json_object = JsonObject.from_json(json.load(f))
                return json_object.cache, json_object.size
        except Exception as e:
            print(f"MintInstall: Cannot open reviews cache: {e}")
            return {}, 0

    def _save_cache(self, cache, size):
        path = Path(REVIEWS_CACHE)
        with self._cache_lock:
            try:
                with path.open(mode='w', encoding="utf8") as f:
                    pobj = JsonObject(cache, size)
                    json.dump(pobj, f, default=lambda o: o.__dict__, indent=4)
            except Exception as e:
                print(f"MintInstall: Could not save review cache: {e}")

    def _update_cache(self):
        thread = threading.Thread(target=self._update_reviews_thread)
        thread.start()

    @print_timing
    def _update_reviews_thread(self):
        success = multiprocessing.Value('b', False)
        current_size = multiprocessing.Value('d', self._size)
        self.proc = multiprocessing.Process(target=self._update_cache_process, args=(success, current_size))
        self.proc.start()
        self.proc.join()
        self.proc = None

        if success.value:
            with self._cache_lock:
                self._reviews, self._size = self._load_cache()
                GLib.idle_add(self.emit_reviews_updated)

    def emit_reviews_updated(self, data=None):
        self.emit("reviews-updated")

    def _update_cache_process(self, success, current_size):
        new_reviews = {}
        try:
            r = requests.head("https://community.linuxmint.com/data/new-reviews.list", timeout=10)
            if r.status_code == 200:
                if int(r.headers.get("content-length", 0)) != current_size.value:
                    r = requests.get("https://community.linuxmint.com/data/new-reviews.list", timeout=30)
                    last_package = None
                    for line in r.iter_lines():
                        decoded = line.decode()
                        elements = decoded.split("~~~")
                        if len(elements) == 5:
                            review = Review(elements[0], float(elements[1]), elements[2], elements[3], elements[4])
                            if last_package and last_package.name == elements[0]:
                                last_package.reviews.append(review)
                            else:
                                if last_package:
                                    last_package.update_stats()
                                last_package = new_reviews.setdefault(elements[0], ReviewInfo(elements[0]))
                                last_package.reviews.append(review)
                    if last_package:
                        last_package.update_stats()
                    self._save_cache(new_reviews, r.headers.get("content-length"))
                    print("MintInstall: Downloaded new reviews")
                    success.value = True
                else:
                    print("MintInstall: No new reviews")
            else:
                print(f"MintInstall: Could not download updated reviews: {r.reason}")
                success.value = False
        except Exception as e:
            print(f"MintInstall: Problem attempting to access reviews URL: {e}")


import os
import threading
import json
import requests
import multiprocessing
from pathlib import Path
from gi.repository import GLib, GObject
from misc import print_timing
from typing import List, Dict, Tuple, Optional

REVIEWS_CACHE = os.path.join(GLib.get_user_cache_dir(), "mintinstall", "reviews.json")

class Review:
    def __init__(self, packagename: str, date: str, username: str, rating: int, comment: str, version: Optional[str] = None):
        """İnceleme nesnesi için constructor."""
        self.packagename = packagename
        self.date = date
        self.username = username
        self.rating = rating
        self.comment = comment
        self.version = version  # Ek alan

    @classmethod
    def from_json(cls, json_data: dict) -> 'Review':
        """JSON verisinden Review nesnesi oluşturur."""
        return cls(**json_data)

class ReviewInfo:
    def __init__(self, name: str, score: float = 0.0, avg_rating: float = 0.0, num_reviews: int = 0, version: Optional[str] = None):
        """Paket incelemeleri hakkında bilgi tutar."""
        self.name = name
        self.reviews: List[Review] = []
        self.categories: List[str] = []  # Boş kalabilir
        self.version = version  # Ek alan
        self.score = score
        self.avg_rating = avg_rating
        self.num_reviews = num_reviews

    def update_stats(self) -> None:
        """Güncellemeler için istatistikleri yeniden hesaplar."""
        self.num_reviews = len(self.reviews)
        sum_rating = sum(review.rating for review in self.reviews)

        if self.num_reviews > 0:
            self.avg_rating = round(sum_rating / self.num_reviews, 1)
            significant_votes = min(10, self.num_reviews)
            missing_votes = 10 - significant_votes
            # Ağırlıklı ortalama hesaplaması
            self.score = round((self.avg_rating * significant_votes + 2.5 * missing_votes) / 10, 1)
        else:
            self.score = 0

    @classmethod
    def from_json(cls, json_data: dict) -> 'ReviewInfo':
        """ReviewInfo nesnesini JSON'dan oluşturur."""
        reviews = [Review.from_json(review) for review in json_data.get("reviews", [])]
        instance = cls(json_data["name"], json_data["score"], json_data["avg_rating"], json_data["num_reviews"], json_data.get("version"))
        instance.reviews = reviews
        return instance

class JsonObject:
    def __init__(self, cache: Dict[str, ReviewInfo], size: int):
        """JSON verilerini tutan nesne."""
        self.cache = cache
        self.size = size

    @classmethod
    def from_json(cls, json_data: dict) -> 'JsonObject':
        """JSON verisinden JsonObject nesnesi oluşturur."""
        cache = {key: ReviewInfo.from_json(info) for key, info in json_data["cache"].items()}
        return cls(cache, int(json_data["size"]))

class ReviewCache(GObject.Object):
    __gsignals__ = {
        'reviews-updated': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    @print_timing
    def __init__(self):
        """ReviewCache sınıfının constructor'ı."""
        super().__init__()
        self._cache_lock = threading.Lock()
        self._reviews, self._size = self._load_cache()
        self.proc = None
        self._update_cache()

    def kill(self) -> None:
        """Çalışmakta olan işlemi sonlandırır."""
        if self.proc is not None:
            self.proc.terminate()
            self.proc = None

    def keys(self) -> List[str]:
        """Önbellekteki tüm paket adlarını döndürür."""
        with self._cache_lock:
            return list(self._reviews.keys())

    def values(self) -> List[ReviewInfo]:
        """Önbellekteki tüm ReviewInfo nesnelerini döndürür."""
        with self._cache_lock:
            return list(self._reviews.values())

    def __getitem__(self, key: str) -> ReviewInfo:
        """Bir paket adı verildiğinde ilgili ReviewInfo nesnesini döndürür."""
        with self._cache_lock:
            return self._reviews.get(key, ReviewInfo(key))

    def __contains__(self, name: str) -> bool:
        """Önbellekte belirli bir paket olup olmadığını kontrol eder."""
        with self._cache_lock:
            return name in self._reviews

    def __len__(self) -> int:
        """Önbellekteki toplam paket sayısını döndürür."""
        with self._cache_lock:
            return len(self._reviews)

    def _load_cache(self) -> Tuple[Dict[str, ReviewInfo], int]:
        """Önbelleği diskteki dosyadan yükler."""
        path = Path(REVIEWS_CACHE)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open(mode='r', encoding="utf8") as f:
                json_object = JsonObject.from_json(json.load(f))
                print(f"MintInstall: Cache loaded successfully with {json_object.size} reviews")
                return json_object.cache, json_object.size
        except Exception as e:
            print(f"MintInstall: Cannot open reviews cache: {e}")
            return {}, 0

    def _save_cache(self, cache: Dict[str, ReviewInfo], size: int) -> None:
        """Önbelleği diske kaydeder."""
        path = Path(REVIEWS_CACHE)
        with self._cache_lock:
            try:
                with path.open(mode='w', encoding="utf8") as f:
                    pobj = JsonObject(cache, size)
                    json.dump(pobj, f, default=lambda o: o.__dict__, indent=4)
                print("MintInstall: Cache saved successfully")
            except Exception as e:
                print(f"MintInstall: Could not save review cache: {e}")

    def _update_cache(self) -> None:
        """Önbelleği günceller."""
        thread = threading.Thread(target=self._update_reviews_thread)
        thread.start()

    @print_timing
    def _update_reviews_thread(self) -> None:
        """İncelemeleri güncellemek için bir iş parçacığı çalıştırır."""
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

    def emit_reviews_updated(self, data=None) -> None:
        """Güncellemeyi diğer bileşenlere bildirir."""
        print("MintInstall: Emitting reviews-updated signal")
        self.emit("reviews-updated")

    def _update_cache_process(self, success: multiprocessing.Value, current_size: multiprocessing.Value) -> None:
        """İnternetten yeni incelemeleri indirir ve önbelleği günceller."""
        new_reviews = {}
        try:
            with requests.get("https://community.linuxmint.com/data/new-reviews.list", timeout=30, stream=True) as r:
                if r.status_code == 200:
                    content_length = int(r.headers.get("content-length", 0))
                    if content_length != current_size.value:
                        last_package = None
                        for line in r.iter_lines():
                            decoded = line.decode()
                            elements = decoded.split("~~~")
                            if len(elements) == 5:
                                review = Review(elements[0], elements[1], elements[2], int(elements[3]), elements[4])
                                if last_package and last_package.name == elements[0]:
                                    last_package.reviews.append(review)
                                else:
                                    if last_package:
                                        last_package.update_stats()
                                    last_package = new_reviews.setdefault(elements[0], ReviewInfo(elements[0]))
                                    last_package.reviews.append(review)
                        if last_package:
                            last_package.update_stats()
                        self._save_cache(new_reviews, content_length)
                        print("MintInstall: Downloaded new reviews")
                        success.value = True
                    else:
                        print("MintInstall: No new reviews")
                else:
                    print(f"MintInstall: Could not download updated reviews: {r.reason}")
                    success.value = False
        except requests.exceptions.RequestException as e:
            print(f"MintInstall: Problem attempting to access reviews URL: {e}")

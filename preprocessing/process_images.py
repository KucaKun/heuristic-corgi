# Processes all the images in the dataset, to a version with only edges, no colors and the same resolution.
import json, os, random
from multiprocessing.pool import Pool
from configuration.datasets import datasets
from configuration.paths import IMAGES_PATH, DATA_PATH, TRAINING_PATH
from PIL import Image, ImageFilter

PIXELS = ["#", "O", "/", "-", " "]
TESTING_TO_TRAINING_RATIO = 0.2
WORKERS = 16


def prepare_dirs(set_name):
    os.makedirs(TRAINING_PATH(set_name), exist_ok=True)
    os.makedirs(TRAINING_PATH(set_name) / "training", exist_ok=True)
    os.makedirs(TRAINING_PATH(set_name) / "testing", exist_ok=True)


def process(image, raw=False, double_filter=True, quantize=False, size=60):
    copied = image.copy()  # copy because thumbnail() is IN PLACE
    copied.thumbnail((size, size))
    copied = copied.resize((size, size))  # stretch if smaller than size
    if not raw:
        copied = copied.filter(ImageFilter.FIND_EDGES)
        if double_filter:
            copied = copied.filter(ImageFilter.FIND_EDGES)
        if quantize:
            (b,) = copied.split()
            b = b.point(lambda i: i // 5 * 5)
            copied = Image.merge("L", (b,))
    return copied


def print_as_ascii(image):
    for y in range(0, image.size[1]):
        for x in range(0, image.size[0]):
            for i, pixel in enumerate(PIXELS):
                value = image.getpixel((x, y))
                threshold = 255 * ((len(PIXELS) - i - 2) / len(PIXELS))
                if value > threshold:
                    print(pixel * 2, end="")
                    break
        print("")


def save(image, set_name, dir, breed, index):
    image.save(TRAINING_PATH(set_name) / dir / (breed + "_" + str(index) + ".jpg"))


def worker(ctr_key_dogs):
    ctr = ctr_key_dogs[0]
    key = ctr_key_dogs[1][0]
    dogs = ctr_key_dogs[1][1]
    with Image.open(IMAGES_PATH / (key + ".jpg")) as im:
        for dog in dogs:
            grayscale = im.convert("L")
            xdiff = int(dog["xmax"]) - int(dog["xmin"])
            ydiff = int(dog["ymax"]) - int(dog["ymin"])
            # Crop to a square from top left corner
            if xdiff < ydiff:
                cropped = grayscale.crop(
                    (
                        int(dog["xmin"]),
                        int(dog["ymin"]),
                        int(dog["xmax"]),
                        int(dog["ymin"]) + xdiff,
                    )
                )
            else:
                cropped = grayscale.crop(
                    (
                        int(dog["xmin"]),
                        int(dog["ymin"]),
                        int(dog["xmin"]) + ydiff,
                        int(dog["ymax"]),
                    )
                )

            dir = (
                "training" if random.random() > TESTING_TO_TRAINING_RATIO else "testing"
            )
            for dataset_name, kwargs in datasets.items():
                processed = process(cropped, **kwargs)
                save(processed, dataset_name, dir, dog["breed"], ctr)

            ctr += 1


if __name__ == "__main__":

    for dataset_name in datasets.keys():
        prepare_dirs(dataset_name)

    with open("dog_annotations.json", "r") as f:
        annotations = json.loads(f.read())
    ctr = 0

    with Pool(processes=WORKERS) as pool:
        pool.map(
            worker, [(ctr, keydogs) for ctr, keydogs in enumerate(annotations.items())]
        )

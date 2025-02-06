FILE = "entity2vec.bern"

if __name__ == "__main__":
    with open(FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
        print(lines[:10])

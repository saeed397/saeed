class ResultManager:

    def __init__(self):
        self.results = []

    def add(self, result):
        self.results.append(result)

    def get_all(self):
        return self.results

    def clear(self):
        self.results = []

    def count(self):
        return len(self.results)

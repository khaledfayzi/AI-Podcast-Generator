class DummySession:
    def __init__(self):
        self.added = []
        self.commit_count = 0
        self.rolled_back = False

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commit_count += 1

    def rollback(self):
        self.rolled_back = True

    def flush(self):
        pass

    def close(self):
        pass


class DummyVoice:
    def __init__(self, stimme_id, name):
        self.stimmeId = stimme_id
        self.name = name
        self.ttsVoice = "de-DE-Wavenet-A"

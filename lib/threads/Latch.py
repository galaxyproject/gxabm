import threading

class CountdownLatch:
    def __init__(self, count = 1):
        self.count = count
        self.lock = threading.Condition


    def count_down(self, count = 1):
        self.count -= count
        if self.count <= 0:
            self.lock.acquire(True)
            self.lock.notifyAll()
            self.lock.release()


    def wait(self):
        self.lock.acquire(True)
        while self.count > 0:
            self.lock.wait()
        self.lock.release()

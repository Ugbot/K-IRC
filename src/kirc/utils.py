import time
import threading

class SnowflakeGenerator:
    """
    Twitter Snowflake-like ID generator.
    
    Structure:
    - 1 bit unused (sign)
    - 41 bits timestamp (milliseconds since epoch)
    - 10 bits machine/node ID
    - 12 bits sequence number
    """
    
    def __init__(self, machine_id: int):
        self.machine_id = machine_id & 0x3FF  # 10 bits
        self.sequence = 0
        self.last_timestamp = -1
        
        self.machine_id_shift = 12
        self.timestamp_shift = 22
        self.sequence_mask = 0xFFF
        
        # Custom epoch (2024-01-01 00:00:00 UTC)
        self.epoch = 1704067200000
        
        self._lock = threading.Lock()

    def _current_timestamp(self) -> int:
        return int(time.time() * 1000)

    def next_id(self) -> int:
        with self._lock:
            timestamp = self._current_timestamp()

            if timestamp < self.last_timestamp:
                raise Exception("Clock moved backwards!")

            if timestamp == self.last_timestamp:
                self.sequence = (self.sequence + 1) & self.sequence_mask
                if self.sequence == 0:
                    # Sequence exhausted, wait for next millisecond
                    while timestamp <= self.last_timestamp:
                        timestamp = self._current_timestamp()
            else:
                self.sequence = 0

            self.last_timestamp = timestamp

            id = ((timestamp - self.epoch) << self.timestamp_shift) | \
                 (self.machine_id << self.machine_id_shift) | \
                 self.sequence
            
            return id

# Global instance
# In a real distributed system, machine_id should be unique per node.
# Here we'll just use a hash of the hostname or something random for now.
import os
import zlib

def _get_machine_id() -> int:
    try:
        # Use hostname hash
        hostname = os.uname().nodename.encode()
        return zlib.crc32(hostname) & 0x3FF
    except:
        return 0

_generator = SnowflakeGenerator(_get_machine_id())

def generate_snowflake_id() -> int:
    return _generator.next_id()

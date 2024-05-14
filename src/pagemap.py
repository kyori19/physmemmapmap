from collections.abc import Iterator
from dataclasses import dataclass
from functools import partial
from os import preadv


@dataclass
class ProcMap:
  address_start: int
  address_end: int
  perms: str
  offset: str
  dev: str
  inode: str
  pathname: str | None = None

  @classmethod
  def from_line(cls, line: str):
    parts = line.split()
    address_start, address_end = map(partial(int, base=16), parts.pop(0).split('-', maxsplit=1))
    return cls(address_start, address_end, *parts)


def maps_from_pid(pid: int) -> Iterator[ProcMap]:
  with open(f'/proc/{pid}/maps') as f:
    lines = f.readlines()

  return map(ProcMap.from_line, lines)


@dataclass
class ProcPageMap:
  present: bool
  swapped: bool
  pfn: int

  @classmethod
  def from_bits(cls, bits: int):
    pfn = bits & 0x7fffffffffffff
    swapped = bool((bits >> 62) & 0b1)
    present = bool((bits >> 63) & 0b1)
    return cls(present, swapped, pfn)


def page_maps_from_maps(pid: int, maps: Iterator[ProcMap]) -> Iterator[ProcPageMap]:
  with open(f'/proc/{pid}/pagemap', 'rb') as f:
    buf = bytearray(8)

    for map in maps:
      for i in range(map.address_start, map.address_end, 4096):
        if preadv(f.fileno(), [buf], int(i * 8 / 4096)) != 8:
          break

        yield ProcPageMap.from_bits(int.from_bytes(buf, byteorder='little'))

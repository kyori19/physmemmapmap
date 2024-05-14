from collections.abc import Iterator
from psutil import Process

from pagemap import ProcPageMap, maps_from_pid, page_maps_from_maps
from plot import plot


def page_maps_from_pid(pid: int, pathname: str | None) -> Iterator[ProcPageMap]:
  maps = maps_from_pid(pid)

  if pathname:
    maps = filter(lambda m: m.pathname == pathname, maps)

  return page_maps_from_maps(pid, maps)


def analyse_procs(procs: list[Process], pathname: str | None, output: str, fixed_width: int | None):
  page_maps_per_pid = {
    proc.pid: page_maps_from_pid(proc.pid, pathname)
    for proc in procs
  }

  per_page = {}
  for pid, page_maps in page_maps_per_pid.items():
    for page_map in page_maps:
      per_page.setdefault((page_map.present, page_map.pfn), set()).add(pid)

  per_pids = {}
  for pfn, pids in per_page.items():
    per_pids.setdefault(tuple(sorted(pids)), set()).add(pfn)

  count_per_pids = {
    pids: len(pfns)
    for pids, pfns in per_pids.items()
  }

  plot(count_per_pids, output, fixed_width)

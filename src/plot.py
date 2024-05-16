from collections.abc import Iterator
from textwrap import fill
import matplotlib.pyplot as plt
from psutil import Process

from pagemap import ProcPageMap, maps_from_pid, page_maps_from_maps

def page_maps_from_pid(pid: int, pathname: str | None) -> Iterator[ProcPageMap]:
  maps = maps_from_pid(pid)

  if pathname:
    maps = filter(lambda m: m.pathname == pathname, maps)

  return page_maps_from_maps(pid, maps)


def count_per_pids(procs: list[Process], pathname: str | None):
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

  return {
    pids: len(pfns)
    for pids, pfns in per_pids.items()
  }


def plot(procs: list[Process], pathname: str | None, output: str, fixed_width: int | None):
  plt.gcf().set_layout_engine('constrained')
  ax = plt.gca()

  sorted_counts = sorted(count_per_pids(procs, pathname).items(), key=lambda x: x[1], reverse=True)

  bar_for_pid = {}
  offset = 0
  for pids, count in sorted_counts:
    for pid in pids:
      bar_for_pid.setdefault(pid, []).append([offset, count])
    offset += count

  procs = sorted(procs, key=lambda proc: proc.pid, reverse=True)
  for i, proc in enumerate(procs, 1):
    bars = bar_for_pid[proc.pid]
    ax.broken_barh(bars, (i - 0.5, 1), facecolors=f'C{i}', edgecolor='black')

  if fixed_width:
    ax.set_xlim(0, fixed_width)

  ax.set_yticks(range(1, len(procs) + 1), labels=map(lambda proc: f'{fill(' '.join(proc.cmdline()), width=32, max_lines=3)} - {proc.pid}', procs))

  plt.savefig(output)
  plt.show()
  print(f'plot saved to {output}')
